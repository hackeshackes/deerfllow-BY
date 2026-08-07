"""RBAC → ABAC migration scanner (v1.7 M2.7).

Scans ``app/gateway/**/routers/*.py`` for owner-gating — ``require_owner_user``
calls or inline ``role == "owner"`` checks — and emits a *candidate*
``policies.json`` the operator reviews before applying. It never auto-applies
policy; it produces a reviewed scaffold that mirrors current owner-only
behavior so the operator can flip specific routers to the declarative gate.

Usage:

    python -m app.gateway.abac.migrate --dry-run          # print a report
    python -m app.gateway.abac.migrate --output policies.json --apply
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_OWNER_GATE_PATTERNS = (
    re.compile(r"require_owner_user\s*\("),
    re.compile(r"\.role\s*==\s*['\"]owner['\"]"),
    re.compile(r"\.role\s*in\s*[\(\s]*['\"]owner", re.IGNORECASE),
)


def derive_verb_from_prefix(prefix: str) -> str:
    """Turn an API prefix into a short action verb for policy naming.

    ``/api/admin/secrets`` → ``secrets``; ``/api/admin/token-usage`` →
    ``token-usage``; trailing slashes are ignored.
    """
    cleaned = prefix.rstrip("/")
    if not cleaned:
        return "default"
    segment = cleaned.rsplit("/", 1)[-1]
    return segment or "default"


def _verb_from_filename(path: str) -> str:
    """Derive a stable verb from a router filename.

    ``admin_secrets.py`` / ``routers/admin_secrets.py`` → ``secrets``.
    """
    stem = Path(path).stem  # strips .py
    stem = re.sub(r"_(router|routes)$", "", stem)  # *_router → *
    stem = stem.removeprefix("admin_")
    return stem if stem else "gate"


def _is_owner_gated(source: str) -> bool:
    return any(pattern.search(source) for pattern in _OWNER_GATE_PATTERNS)


def scan_text(path: str, source: str) -> dict | None:
    """Return ``{path, verbs=[verb]}`` for an owner-gated router file."""
    if not _is_owner_gated(source):
        return None
    return {"path": path, "verbs": [_verb_from_filename(path)]}


def scan_directory(root: str | Path) -> list[dict]:
    """Walk ``root`` for router files and report owner-gated ones."""
    root_p = Path(root)
    findings: list[dict] = []
    for py in sorted(root_p.rglob("*.py")):
        try:
            source = py.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = py.relative_to(root_p).as_posix()
        found = scan_text(rel, source)
        if found:
            findings.append(found)
    return findings


def emit_policies_json(findings: list[dict]) -> str:
    """Render the operator-review candidate ``policies.json``."""
    policies = []
    for f in findings:
        verb = f["verbs"][0] if f.get("verbs") else "gate"
        policies.append(
            {
                "id": f"owner-only-{verb}",
                "name": f"owner-only-{verb} (from {f['path']})",
                "effect": "allow",
                "combiner": "all_of",
                "applies_to": [verb],
                "conditions": [{"op": "equals", "path": "subject.role", "value": "owner"}],
            }
        )
    payload = {"version": 1, "policies": policies}
    return json.dumps(payload, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rbac-to-abac", description="Scan owner-gated routers into a candidate ABAC policies file."
    )
    parser.add_argument("--root", default="app/gateway", help="directory to scan")
    parser.add_argument("--output", default="policies.candidates.json", help="candidate output path")
    parser.add_argument("--dry-run", action="store_true", help="print findings without writing")
    args = parser.parse_args(argv)

    findings = scan_directory(args.root)
    if args.dry_run:
        for f in findings:
            print(f"{f['path']}: owner-gated ({', '.join(f['verbs'])})")
        return 0

    out = Path(args.output)
    out.write_text(emit_policies_json(findings), encoding="utf-8")
    print(f"wrote candidate policies to {out} ({len(findings)} owner-gated routers)")
    return 0


__all__ = [
    "derive_verb_from_prefix",
    "emit_policies_json",
    "scan_directory",
    "scan_text",
]


if __name__ == "__main__":
    import sys

    sys.exit(main())