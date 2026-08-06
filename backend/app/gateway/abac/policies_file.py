"""Declarative ABAC policies-file loader (v1.7 M2.2).

Parses the policies file described in ``docs/abac/policy-spec.md`` into
``AttributePolicy`` instances the ``abac.evaluate`` engine can consume.

Format contract (JSON or YAML, detected by extension):

    {"version": 1,
     "policies": [
        {"id": "owner-only", "effect": "allow",
         "combiner": "all_of",                # default all_of
         "applies_to": ["publish"],           # optional; empty = all verbs
         "conditions": [{"op": "equals", "path": "subject.role", "value": "owner"}]}
     ]}

Safety: this is a *validating* loader. Unknown ops, bad effects, missing /
duplicate ids, and malformed files raise ``ValueError`` — callers get a
last-good set via :func:`resolve_policies`, never a half-parsed one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover - yaml is optional
    yaml = None  # type: ignore[assignment]

from .evaluator import AttributePolicy, Operator
from .policies import OwnerOnlyPolicy, WorkspaceMemberPolicy

VALID_EFFECTS = {"allow", "deny"}
VALID_COMBINERS = {"all_of", "any_of"}
VALID_OPS = {"equals", "in"}

# Fallback to the built-in presets (v1.6.1 RBAC-equivalent behavior).
_BUILTIN_POLICIES: list[AttributePolicy] = [
    OwnerOnlyPolicy(),
    WorkspaceMemberPolicy(),
]


def _parse_condition(c: Any) -> Operator:
    """Parse one condition dict into an :class:`Operator`."""
    if not isinstance(c, dict):
        raise ValueError(f"condition must be an object, got {type(c).__name__}")
    op = c.get("op")
    if op not in VALID_OPS:
        raise ValueError(f"unsupported operator {op!r} (expected equals|in)")
    path = c.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("condition requires a non-empty 'path'")
    value = c.get("value")
    if op == "equals":
        return Operator.equals(path, value)
    return Operator.in_(path, value)


def validate_policy_dict(d: dict) -> AttributePolicy:
    """Parse and validate one policy dict into a callable policy.

    Raises ``ValueError`` on any schema violation — never partially loaded.
    """
    if not isinstance(d, dict):
        raise ValueError(f"policy must be an object, got {type(d).__name__}")
    pid = d.get("id")
    if not isinstance(pid, str) or not pid:
        raise ValueError("policy requires a non-empty 'id'")

    effect = d.get("effect")
    if effect not in VALID_EFFECTS:
        raise ValueError(f"invalid 'effect' {effect!r} (expected allow|deny)")

    combiner = d.get("combiner", "all_of")
    if combiner not in VALID_COMBINERS:
        raise ValueError(f"invalid 'combiner' {combiner!r} (expected all_of|any_of)")

    applies_to = d.get("applies_to", [])
    if not isinstance(applies_to, list):
        raise ValueError("'applies_to' must be a list (or omitted)")
    verbs: tuple[tuple[str, ...], ...] = tuple((v,) for v in applies_to if isinstance(v, str))

    operators = tuple(_parse_condition(cond) for cond in d.get("conditions", []))

    name = d.get("name") or pid
    if not isinstance(name, str):
        raise ValueError("'name' must be a string")

    return AttributePolicy(
        name=name,
        applies_to=verbs,
        operators=operators,
        combinator=combiner,
        effect=effect,
    )


def _read_document(path: Path) -> dict:
    """Read + parse a JSON or YAML policies file into a top-level dict."""
    if path.suffix.lower() in (".yaml", ".yml"):
        if yaml is None:
            raise ValueError("PyYAML is required to load .yaml policies files")
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    else:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("policies file must be a JSON object with a 'policies' list")
    return data


def load_policies_file(path: str | Path) -> list[AttributePolicy]:
    """Parse and validate the policies file at *path*.

    Raises ``FileNotFoundError`` if the file is absent; ``ValueError`` on
    malformed content or policy schema violations.
    """
    p = Path(path)
    data = _read_document(p)
    raw = data.get("policies")
    if not isinstance(raw, list) or not raw:
        raise ValueError("policies file must contain a non-empty 'policies' list")

    policies = [validate_policy_dict(pol) for pol in raw]
    ids = [pol.name for pol in policies]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate policy id in policies file")
    return policies


def resolve_policies(path: str | Path | None) -> list[AttributePolicy]:
    """Return the policies for *path*, falling back to built-in presets.

    When *path* is ``None`` or a missing file, the built-in presets are
    returned — preserving v1.6.1 RBAC-equivalent behavior.
    """
    if not path:
        return list(_BUILTIN_POLICIES)
    try:
        return load_policies_file(path)
    except FileNotFoundError:
        return list(_BUILTIN_POLICIES)


class PoliciesCache:
    """Mtime-aware policy cache that keeps the last-good set.

    Mirrors the config mtime-invalidation pattern in
    ``deerflow.config.app_config``: the first :meth:`get` loads and records the
    file mtime; a later :meth:`get` re-loads only when the on-disk mtime
    increases. On a bad edit, the previous good set is retained (fail-safe)
    rather than raised — a malformed policies file must never yield an empty or
    half-parsed authorization set without a signal.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._policies: list[AttributePolicy] | None = None
        self._mtime: float | None = None

    def _current_mtime(self) -> float | None:
        try:
            return self._path.stat().st_mtime
        except FileNotFoundError:
            return None

    def get(self) -> list[AttributePolicy]:
        """Return the current policy list, reloading on mtime change.

        Falls back to built-in presets if the file is absent; keeps the last
        good set if a reload fails.
        """
        mtime = self._current_mtime()

        if self._policies is None:
            self._policies = resolve_policies(self._path)
            self._mtime = mtime
            return list(self._policies)

        # Reload only when the file changed (different mtime).
        if mtime == self._mtime:
            return list(self._policies)

        try:
            self._policies = load_policies_file(self._path)
            self._mtime = mtime
        except (FileNotFoundError, ValueError):
            # Last-good set stays active; the reload is intentionally soft.
            pass
        return list(self._policies)


__all__ = [
    "load_policies_file",
    "resolve_policies",
    "validate_policy_dict",
    "PoliciesCache",
    "OwnerOnlyPolicy",
    "WorkspaceMemberPolicy",
]