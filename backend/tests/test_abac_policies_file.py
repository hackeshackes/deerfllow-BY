"""Unit tests for the declarative ABAC policies-file loader (v1.7 M2.2).

Covers:
1. ``load_policies_file`` parses the JSON schema from ``docs/abac/policy-spec.md``
   into ``AttributePolicy`` instances and they evaluate via ``abac.evaluate``.
2. YAML is accepted alongside JSON.
3. Invalid files (unknown op, bad effect, missing id, duplicate id, empty
   list) are rejected with ``ValueError`` — never half-loaded.
4. ``resolve_policy_source`` falls back to the built-in presets when no file
   exists (backward-compatible RBAC behavior).
5. mtime-aware reload keeps the last-good set on a bad edit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.gateway.abac.evaluator import (
    Action,
    AttributePolicy,
    Resource,
    Subject,
    evaluate,
)
from app.gateway.abac.policies_file import (
    load_policies_file,
    resolve_policies,
    validate_policy_dict,
)


def _owner(role: str = "owner", workspaces: list[str] | None = None) -> Subject:
    return Subject(id="u-1", role=role, attrs={"workspaces": workspaces or []})


def _resource() -> Resource:
    return Resource(type="thread", id="t1", attrs={"workspace_id": "ws-1"})


OWNER_ONLY = {
    "version": 1,
    "policies": [
        {
            "id": "owner-only",
            "effect": "allow",
            "combiner": "all_of",
            "applies_to": ["publish"],
            "conditions": [{"op": "equals", "path": "subject.role", "value": "owner"}],
        }
    ],
}


# ---------------------------------------------------------------------------
# Raw dict validation
# ---------------------------------------------------------------------------


class TestValidatePolicyDict:
    def test_accepts_valid_policy(self):
        p = validate_policy_dict(
            {
                "id": "a",
                "effect": "allow",
                "conditions": [{"op": "equals", "path": "subject.role", "value": "owner"}],
            }
        )
        assert isinstance(p, AttributePolicy)
        assert p.name == "a"
        assert p.effect == "allow"

    def test_empty_conditions_all_of_matches(self):
        p = validate_policy_dict({"id": "x", "effect": "allow", "conditions": []})
        assert p.matches_action(Action("anything"))
        assert p.evaluate(_owner(), _resource(), Action("anything")) is True

    def test_invalid_effect_rejected(self):
        with pytest.raises(ValueError):
            validate_policy_dict({"id": "a", "effect": "maybe"})

    def test_unsupported_op_rejected(self):
        with pytest.raises(ValueError):
            validate_policy_dict(
                {"id": "a", "effect": "allow", "conditions": [{"op": "regexp", "path": "a", "value": "x"}]}
            )

    def test_missing_id_rejected(self):
        with pytest.raises(ValueError):
            validate_policy_dict({"effect": "allow"})

    def test_invalid_combiner_rejected(self):
        with pytest.raises(ValueError):
            validate_policy_dict(
                {"id": "a", "effect": "allow", "combiner": "every", "conditions": []}
            )

    def test_default_name_is_id(self):
        p = validate_policy_dict({"id": "my-policy", "effect": "allow", "conditions": []})
        assert p.name == "my-policy"


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------


class TestLoadPoliciesFile:
    def test_loads_json_owner_only(self, tmp_path: Path):
        f = tmp_path / "policies.json"
        f.write_text(json.dumps(OWNER_ONLY))
        policies = load_policies_file(f)

        allowed = evaluate(
            subject=_owner("owner"), resource=_resource(), action=Action("publish"), policies=policies
        )
        denied = evaluate(
            subject=_owner("member"), resource=_resource(), action=Action("publish"), policies=policies
        )
        assert allowed.allowed
        assert not denied.allowed
        assert denied.reason == "no matching policy"

    def test_loads_yaml(self, tmp_path: Path):
        f = tmp_path / "policies.yaml"
        f.write_text(
            "version: 1\n"
            "policies:\n"
            "  - id: owner-only\n"
            "    effect: allow\n"
            "    combiner: all_of\n"
            "    applies_to: [publish]\n"
            "    conditions:\n"
            "      - op: equals\n"
            "        path: subject.role\n"
            "        value: owner\n"
        )
        policies = load_policies_file(f)
        assert len(policies) == 1
        assert policies[0].name == "owner-only"
        assert evaluate(
            subject=_owner(), resource=_resource(), action=Action("publish"), policies=policies
        ).allowed

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_policies_file(tmp_path / "nope.json")

    def test_empty_policies_list_rejected(self, tmp_path: Path):
        f = tmp_path / "policies.json"
        f.write_text(json.dumps({"version": 1, "policies": []}))
        with pytest.raises(ValueError, match="non-empty 'policies'"):
            load_policies_file(f)

    def test_malformed_json_rejected(self, tmp_path: Path):
        f = tmp_path / "policies.json"
        f.write_text("{ not json !!")
        with pytest.raises(ValueError):
            load_policies_file(f)

    def test_duplicate_id_rejected(self, tmp_path: Path):
        f = tmp_path / "policies.json"
        f.write_text(
            json.dumps(
                {
                    "version": 1,
                    "policies": [
                        {"id": "a", "effect": "allow", "conditions": []},
                        {"id": "a", "effect": "allow", "conditions": []},
                    ],
                }
            )
        )
        with pytest.raises(ValueError, match="duplicate"):
            load_policies_file(f)


# ---------------------------------------------------------------------------
# Resolution + hot reload
# ---------------------------------------------------------------------------


class TestResolveAndReload:
    def test_falls_back_to_builtin_presets_when_no_file(self, tmp_path: Path):
        policies = resolve_policies(str(tmp_path / "missing.json"))
        names = {p.name for p in policies}
        assert "owner-only" in names
        assert "workspace-member" in names

    def test_reloads_when_mtime_changes(self, tmp_path: Path):
        f = tmp_path / "policies.json"
        f.write_text(json.dumps(OWNER_ONLY))
        first = load_policies_file(f)

        edited = {
            "version": 1,
            "policies": [
                {"id": "everyone", "effect": "allow", "conditions": []},
                {"id": "no-one", "effect": "deny", "combiner": "any_of", "conditions": []},
            ],
        }
        f.write_text(json.dumps(edited))
        second = load_policies_file(f)
        assert [p.name for p in second] == ["everyone", "no-one"]
        # the old set is untouched by the new load
        assert [p.name for p in first] == ["owner-only"]

    def test_cache_keeps_last_good_on_bad_edit(self, tmp_path: Path):
        """A malformed edit must leave the previous good set active."""
        from app.gateway.abac.policies_file import PoliciesCache

        f = tmp_path / "policies.json"
        f.write_text(json.dumps(OWNER_ONLY))
        cache = PoliciesCache(path=str(f))
        assert [p.name for p in cache.get()] == ["owner-only"]

        # Corrupt the file in place with a bumped mtime.
        f.write_text("{ deliberately malformed !!")
        # Cache reloads on mtime change but keeps last-good when the new parse fails.
        assert [p.name for p in cache.get()] == ["owner-only"]


# ---------------------------------------------------------------------------
# Builtin resolution contract
# ---------------------------------------------------------------------------


class TestBuiltinFallbackHumanReadable:
    def test_builtin_owner_only_blocks_member(self):
        policies = resolve_policies(str(Path(".") / "does-not-exist.json"))
        assert not evaluate(
            subject=_owner("member"), resource=_resource(), action=Action("publish"), policies=policies
        ).allowed
        assert evaluate(
            subject=_owner("owner"), resource=_resource(), action=Action("publish"), policies=policies
        ).allowed