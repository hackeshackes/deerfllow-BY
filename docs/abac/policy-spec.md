# DeerFlow ABAC Policy Specification

**Version:** v1.0 · **Date:** 2026-08-06 · **Status:** v1.7 (M2)

This document is the source-of-truth for the DeerFlow ABAC **policies file
format**. It defines how an operator authors, loads, and hot-reloads
authorization policy without changing code. The runtime evaluator
(`abac/evaluator.py`) and built-in presets (`abac/policies.py`) implement the
semantics defined here.

---

## 1. File location & lifecycle

- **Canonical path:** `backend/.deer-flow/policies.json` (gitignored — operator-owned).
  A `*.yaml` file at the same path is accepted; the loader chooses by extension.
- **Startup:** the gateway loads the file once at startup.
- **Reload:** the file is re-read when its mtime changes (polled, mirroring the
  existing config mtime-invalidation pattern) or on `SIGHUP`. A malformed edit
  leaves the **last-good** policy set in effect (fail-safe — never half-load).
- **Fallback:** if no file exists, the built-in in-code presets are used, which
  preserve the v1.6.1 RBAC-equivalent behavior (see §4).

## 2. Top-level shape

```jsonc
{
  "version": 1,                       // integer; bumped on publish (advisory in v1.7)
  "policies": [ /* ... one or more policy objects (see §3) */ ]
}
```

`version` is informational (shown in the editor, not used in evaluation).
`policies` is an **ordered** list; the engine uses deterministic first-match (see §5).

## 3. Policy object

| Field        | Type              | Required | Meaning                                                     |
|--------------|-------------------|----------|-------------------------------------------------------------|
| `id`         | string            | yes      | Unique, URL-safe identifier; used in audit logs           |
| `name`       | string            | no       | Human label; defaults to `id`                             |
| `effect`     | `allow`/`deny`    | yes      | Outcome when this policy matches                         |
| `combiner`   | `all_of`/`any_of` | no       | How the conditions combine; default `all_of`  |
| `applies_to` | list[string]      | no       | Verbs this policy applies to; empty ⇒ all verbs          |
| `conditions` | list[condition]   | no       | Operator AST; empty + `all_of` ⇒ always match             |

### Condition (operator)

```jsonc
{
  "op":    "equals" | "in",
  "path":  "subject.role",
  "value": "owner"                    // for `equals`: a literal
                                     // for `in`: a literal list, or a dotted path
}
```

- `path` is a dotted path into the `(subject, resource, action)` triple. The
  first segment is `subject` / `resource` / `action`; later segments resolve a
  direct field (`role`, `id`, `type`) or an `attrs[...]` key (e.g.
  `subject.workspaces`, `resource.workspace_id`).
- `equals`: both `path` and `value` must resolve to non-None for a matching
  comparison.
- `in`: `path` is a scalar; `value` is either a literal list or a dotted path
  resolving to a list (e.g. `subject.workspaces`).

### Examples

Owner-only (mirrors `OwnerOnlyPolicy`):

```jsonc
{
  "id": "owner-only",
  "effect": "allow",
  "combinator": "all_of",
  "applies_to": ["write", "publish", "execute", "delete", "rollback"],
  "conditions": [ { "op": "equals", "path": "subject.role", "value": "owner" } ]
}
```

Workspace member (owners allowed; members allowed when `resource.workspace_id`
is in `subject.workspaces` — mirrors `WorkspaceMemberPolicy`):

```jsonc
{
  "id": "workspace-member",
  "effect": "allow",
  "combinator": "any_of",
  "applies_to": ["read", "execute", "publish", "write"],
  "conditions": [
    { "op": "equals", "path": "subject.role", "value": "owner" },
    { "op": "in",     "path": "resource.workspace_id", "value": "subject.workspaces" }
  ]
}
```

Explicit deny (evaluate before allow rules for the same action):

```jsonc
{
  "id": "deny-staff-on-prod-execute",
  "effect": "deny",
  "applies_to": ["execute"],
  "conditions": [
    { "op": "equals", "path": "resource.environment", "value": "prod" },
    { "op": "in",     "path": "subject.role", "value": ["staff", "contractor"] }
  ]
}
```

## 4. Built-in fallback presets

When no policy file is present, the runtime uses two in-code policies
(identical v1.6.1 behavior):

1. `owner-only` — `allow` when `subject.role == "owner"`.
2. `workspace-member` — `allow` when owner, OR the resource's `workspace_id`
   is in the subject's `workspaces`.

This preserves backward compatibility: existing RBAC `role == "owner"` gaunts
behave exactly as before an operator introduces a policy file.

## 5. Evaluation semantics (precedence)

1. A policy is a **candidate** if `applies_to` is empty (all verbs) or
   includes the current `action.verb`.
2. A candidate **matches** if its `conditions` evaluate per the combinator;
   empty `conditions` + `all_of` always matches.
3. The **first matching** policy's `effect` wins (`allow` / `deny`).
4. If **no** policy matches, the result is **deny** (fail-closed).

Order matters: put `deny` rules **before** `allow` rules for the same action so
denials are evaluated first (first-match is deterministic).

## 6. Validation & errors

- Unknown top-level keys, missing/duplicate `id`, an invalid `effect`, or an
  unsupported `op` are **hard errors** → the file is rejected and the last-good
  policy set remains active.
- An empty `policies` array is rejected (would deny everything with no allow).
- Unknown verbs in `applies_to` are warnings, not errors (forward-compatible).

## 7. Scope & non-goals (v1.7)

- One authorization context driving every admin-gated surface (thread, workflow,
  connector, quota, publish) — this file format is that driver.
- NOT a full XACML engine; no evaluated user code; single file only.
  The operator set is fixed (no new operators without a code change).

## 8. References

- Evaluator semantics: `app/gateway/abac/evaluator.py`
- Presets: `app/gateway/abac/policies.py`
- Loader: `app/gateway/abac/policies_file.py`
- Plan: `docs/superpowers/plans/2026-08-06-v1.7-implementation-plan.md` (M2)