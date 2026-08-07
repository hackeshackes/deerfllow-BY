"""Unit tests for the RBAC→ABAC migration scanner (v1.7 M2.7).

Scans router files for owner-gating (``require_owner_user`` / inline
``role == "owner"``) and emits a *candidate* ABAC ``policies.json`` the
operator reviews before applying. The scanner functions are pure, so they are
tested against fixture router source (no live filesystem walk).
"""

from __future__ import annotations

import json

from app.gateway.abac.migrate import (
    derive_verb_from_prefix,
    emit_policies_json,
    scan_text,
)


class TestScanText:
    def test_detects_require_owner_user(self):
        code = (
            "from app.gateway.auth import require_owner_user\n"
            "@router.get('')\n"
            "async def get_secrets(request):\n"
            "    require_owner_user(request)\n"
        )
        found = scan_text("routers/admin_secrets.py", code)
        assert found is not None
        assert found["path"].endswith("admin_secrets.py")
        assert found["verbs"]  # at least one derived owner-gated verb

    def test_detects_inline_role_owner(self):
        code = (
            "@router.get('')\n"
            "async def get_models(request):\n"
            "    user = require_user(request)\n"
            "    if user.role == 'owner':\n"
            "        return {}\n"
        )
        assert scan_text("routers/models.py", code) is not None

    def test_no_gate_when_absent(self):
        code = "@router.get('')\nasync def list_ok(request):\n    return []\n"
        assert scan_text("routers/public.py", code) is None


class TestPrefixVerb:
    def test_verb_from_api_prefix(self):
        assert derive_verb_from_prefix("/api/admin/secrets") == "secrets"
        assert derive_verb_from_prefix("/api/admin/token-usage") == "token-usage"
        assert derive_verb_from_prefix("/api/threads") == "threads"


class TestEmitPoliciesJson:
    def test_generates_owner_only_policy_per_gate(self):
        findings = [
            {"path": "app/gateway/routers/admin_secrets.py", "verbs": ["secrets"]},
            {"path": "app/gateway/routers/models.py", "verbs": ["models"]},
        ]
        payload = json.loads(emit_policies_json(findings))
        assert payload["version"] == 1
        assert isinstance(payload["policies"], list)
        ids = [p["id"] for p in payload["policies"]]
        assert "owner-only-secrets" in ids
        assert "owner-only-models" in ids

    def test_emits_comment_outline_is_reviewable(self):
        findings = [{"path": "app/gateway/routers/admin_secrets.py", "verbs": ["secrets"]}]
        text = emit_policies_json(findings)
        # The operator sees a review scaffold, not an auto-applied policy.
        assert "version" in text and "policies" in text