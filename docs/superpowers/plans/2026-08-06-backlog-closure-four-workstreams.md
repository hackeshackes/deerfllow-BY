# Remaining Backlog Closure — Four Workstreams

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Context:** Follow-up to the 2026-08-06 review of lingering repo issues. Four independent workstreams, each with its own branch, tests, and merge gate. Order of execution matters (Ws1 bookkeeping is trivial and should land first to unblock the docs tree; Ws2 dependency bumps should be verified before the larger Ws3 code work so their regression signal stays isolated).

## Verified Starting State (do not re-derive)

- `origin/main` == local `main` == `21759b40`, not behind/ahead (fetched 2026-08-06).
- Gateway proxy (Issue #1) code, `frontend/tests/next-config.test.ts` (6 tests), and CHANGELOG Unreleased entry **are already committed and pushed**. Issue #1 is **CLOSED**. Only the plan/spec docs are untracked (`??`) with all checkboxes unchecked.
- Open dependabot PRs: #14 next 16.1.7→16.2.11, #15 better-auth 1.4.18→1.6.22 (security), #18 pyjwt 2.12.0→2.13.0, #19 pyasn1 0.6.3→0.6.4, #20 aiohttp 3.13.4→3.14.3, #21 postcss 8.5.6→8.5.23 (security).
- Open roadmap enh issues: #10 (ABAC full), #11 (canvas connector quota panel), #12 (multi-region secret replication), #13 (Slack Socket Mode).
- Code gaps: `runtime/runs/worker.py:175` checkpoint rollback (Phase 2 stub); DingTalk/WeCom connectors token re-fetch on 401 is documented-but-unimplemented.
- `backend/.venv/bin/python` exists (venv). Frontend uses `pnpm@10.26.2`, `package.json` scripts: `check`=eslint+tsc+vitest, `test`, `build`, `format:write`.
- `CachedToken` (`connectors/token_refresh.py`) already has `invalidate()` + single-flight `get()`. Connectors have a broad test suite (`test_connectors_*.py`, `test_dingtalk_connector.py`, `test_wecom_connector.py`) but **no worker rollback tests** exist.

---

## Workstream 1 (Ws1) — Gateway plan-doc bookkeeping (P0, cheapest)

Now that the code is merged to `origin/main` (not a feature branch), the original plan's Task 4 (branch → PR → merge) no longer applies. Re-scope to pure bookkeeping: mark the workstream committed-and-merged, commit the docs, and stop. **No code changes.**

**Files:**
- Track: `docs/superpowers/plans/2026-07-24-development-gateway-api-fallback-proxy.md`
- Track: `docs/superpowers/specs/2026-07-24-development-gateway-api-fallback-proxy-design.md`

- [ ] **Step 1: Mark the original plan's implementation steps as done**
  - Toggle every `- [ ]` under Task 1, Task 2, Task 3 to `- [x]` in `docs/.../gateway-api-fallback-proxy.md` — these were actually executed and verified (implementation commit `2176b40`, tests 6/6 green, `tsc --noEmit` clean, `pnpm build` reported OK in review).
- [ ] **Step 2: Rework Task 4 into a Deferral note**
  - Replace the Task 4 publishing steps with a short note: "Implementation merged to `main` as commit `2176b40`; Issue #1 closed on `2026-07-24`. A follow-up feature-branch/PR step is intentionally skipped because the change is already released."
- [ ] **Step 3: Commit the docs**
  ```bash
  git add docs/superpowers/plans/2026-07-24-development-gateway-api-fallback-proxy.md docs/superpowers/specs/2026-07-24-development-gateway-api-fallback-proxy-design.md
  git commit -m "docs: close out gateway fallback plan (merged to main, issue #1 closed)"
  ```
- [ ] **Step 4: Verify** — `git status --short` is clean; `git log -1 --oneline` shows the docs commit.

**Acceptance:** Both docs tracked; no `??` files remain; no code files touched. **Do not open a PR** for Ws1 (the change is already on main; a PR-from-main would be a no-op).

---

## Workstream 2 (WS2) — Dependabot dependency upgrades (requires CI green)

**Goal:** land 6 dependabot PRs with verified safety. Because better-auth and next (and postcss CSS) are the security-relevant/breaking-risk ones, order them so individually-verified bumps are merged gradually, re-running the quality gate after each.

### WS2a — Truly non-breaking (backend) PRs: #18 pyjwt, #19 pyasn1, #20 aiohttp
These are patch-level within an already-resolved version range and carry no schema/migration change.

- [ ] **Step 1: Run backend gate before any merge**
  ```bash
  cd backend && .venv/bin/python -m pytest -q
  ```
  Record the pre-merge baseline (expect ~206 test files, all green).
- [ ] **Step 2: Merge the three backend patch PRs via GitHub UI or `gh`**
  ```bash
  gh pr merge 20 --merge --delete-branch
  gh pr merge 19 --merge --delete-branch
  gh pr merge 18 --merge --delete-branch
  ```
- [ ] **Step 3: Re-run the backend gate after merges** — repeat Step 1. Any failure → generate a revert item in the backlog and report before continuing.

### WS2b — postcss bump PR #21 (security)
- [ ] **Step 1: Verify no frontend regression** — `cd frontend && pnpm install && pnpm check && pnpm build` (baseline must be green before this bump).
- [ ] **Step 2: Merge** `gh pr merge 21 --merge --delete-branch`.
- [ ] **Step 3: Re-run `pnpm check && pnpm build`.**

### WS2c — better-auth 1.4.18→1.6.22 PR #15 (security; major-version jump)
This may include breaking changes to the auth API surface. Do NOT merge blind.
- [ ] **Step 1: Inspect the PR diff and changelog** (WebFetch the better-auth release notes / the dependency diff).
- [ ] **Step 2: Check whether the repo pins auth usage to APIs that changed.** Grep `frontend/src` and `backend` for `betterAuth`, `createAuth`, `auth.api`, cookies/session calls south of the bump. Confirm only additive/stable APIs are used.
- [ ] **Step 3: If the diff is additive** and `pnpm check && pnpm build` stays green → merge `gh pr merge 15 --merge --delete-branch`.
- [ ] **Step 4: If the build breaks**, rebase the bump commit locally onto `better-auth-1.6.22`'s branch, add the minimal compatibility fix **with a test** in the same PR, and re-run the gate. Do not merge until green.
- **Hard rule:** better-auth touchpoints are session/login/security-sensitive → after merging, run a real auth smoke test (see Ws4 verification) and the backend auth test files.

### WS2d — next 16.1.7→16.2.11 PR #14 (framework patch)
- [ ] **Step 1: Inspect the diff** for server/client boundary or `next/*` API changes vs the current pinned code.
- [ ] **Step 2: Run `pnpm check && pnpm build`** on the branch. Confirm no rewrite-phase regression via `pnpm vitest run tests/next-config.test.ts`.
- [ ] **Step 3: Merge** `gh pr merge 14 --merge --delete-branch`, then re-run the focused next-config tests on `main`.

---

## Workstream 3 (WS3) — Checkpoint rollback (code gap; TDD)

**Files:**
- Modify: `packages/harness/deerflow/runtime/runs/worker.py` (~line 175 `TODO(Phase 2)`)
- Create: `backend/tests/test_runtime_worker_rollback.py`
- Reference: `checkpointer` interface (delete/revert API) used by the run worker. Confirm the actual API before writing code — do not assume `adelete()`; verify the langgraph checkpointer surface in the repo.

- [ ] **Step 1: Verify the checkpointer API surface.** Grep the repo for `checkpointer`, `adelete`, `aupdate_state`, `aload` in `runtime/` to learn the real method available to revert a thread to `pre_run_checkpoint_id`. Record the exact call in the TODO body comment.
- [ ] **Step 2 (TDD): Write the failing test first.** A `test_rollback_*` that constructs a fake checkpointer recording calls, runs the rollback path (abort action = `rollback`, `pre_run_checkpoint_id` set), and asserts: (a) `set_status(RunStatus.error)` is called, (b) the checkpointer was asked to revert to `pre_run_checkpoint_id`, (c) the fallback `except` path logs a warning and still sets error status (verifies no crash path). Run it — expect RED because the body is `pass`.
- [ ] **Step 3 (GREEN): implement.** In `worker.py`, replace the `pass` body: call the checkpointer revert using the API confirmed in Step 1; keep the surrounding `try/except Exception -> logger.warning` so an external revert failure still yields a graceful `error` status.
- [ ] **Step 4: run the rollback test + the broader runtime tests** — `cd backend && .venv/bin/python -m pytest tests/test_runtime_worker_rollback.py tests/test_connectors_runtime.py -q`. Confirm no regression.
- [ ] **Step 5: backfill a test for the *non*-rollback abort path** (the `else` branch sets `interrupted`) if not already covered.
- [ ] **Step 6: ruff** `cd backend && .venv/bin/ruff check --fix .` then `.venv/bin/python -m pytest -q` for the full 200+ file suite.
- [ ] **Step 7: Commit** `git commit -am "feat(runtime): full checkpoint rollback on abort (Phase 2)"`.

---

## Workstream 4 (WS4) — Connector token re-fetch on 401

**Ws4a — DingTalk (the one explicitly TODO'd in docstring).**

`CachedToken.invalidate()` exists but the DingTalk connector never calls it on a 401. Reuse that primitive.

- [ ] **Step 1: Locate the DingTalk send path** where a 401 from `api.dingtalk.com` is detected (the code path that "should trigger a re-fetch"). Read the current 401 handling.
- [ ] **Step 2 (TDD): test** `test_dingtalk_connector.py` — simulate a first request returning 401 while the cached token is still "fresh", assert the connector calls `invalidate()` and refetches, and the second attempt succeeds.
- [ ] **Step 3 (GREEN): implement** in `DingTalkConnector`: on upstream 401, call `self._token.invalidate()` then retry once.
- [ ] **Step 4: Run** `cd backend && .venv/bin/python -m pytest tests/test_dingtalk_connector.py tests/test_connectors_token_refresh.py -q`.

**Ws4b — WeCom.**
- [ ] **Step 5: Inspect** `backend/app/gateway/connectors/wecom/connector.py` line ~9 (the same 401-refetch TODO) — confirm the same `CachedToken` usage pattern and reuse the same `invalidate()`-on-401 approach. If WeCom uses a different token structure, adapt.
- [ ] **Step 6 (TDD):** add the WeCom 401-refetch test; implement.
- [ ] **Step 7: ruff + full pytest** repeated, then a single commit per connector (or one combined commit if trivial).

---

## Workstream 5 (WS5) — Backlog (no code this iteration; produce actionable tickets)

**Goal:** convert the 4 roadmap issues into detail-spec'd child tasks. No code changes. Record the PRD/design docs if a future sprint needs them.

- [ ] **Step 1:** Read each open issue (#10, #11, #12, #13) to pull its stated requirements.
- [ ] **Step 2:** For each, produce a `docs/superpowers/specs/2026-08-06-micx-v1.7-<slug>.md` capturing: problem, non-goals, acceptance criteria, affected files, open questions. Keep them tight; this is backlog grooming, not full design.
- [ ] **Step 3:** Update the issue bodies with the acceptance criteria + link the spec doc; re-tag `v1.7` if not set.
- [ ] **Step 4:** Verify `gh issue list --state open` still shows the 4 with the new linkage. Do NOT start implementation.

---

## Cross-cutting verification

After WS1–WS3 (each independently), on `main`:

```bash
cd backend && .venv/bin/python -m pytest -q        # all 200+ files green
cd frontend && pnpm check && pnpm build             # eslint + tsc + vitest + build
cd frontend && pnpm vitest run tests/next-config.test.ts   # proxy rewrite unchanged
```

## Risks & mitigations

- **Checkpointer revert API differs from the comment** → Step 1 of WS3 reads the actual interface first; never assume `delete_revert` name.
- **better-auth 1.6.22 breaking session API** → WS2c inspects the diff + greps usage; if it breaks, fix-with-test in the same PR rather than merging breaking.
- **Next 16.2 rewrite-phase regression** → WS2d explicitly runs the `next-config.test.ts` proxy tests after merge.
- **DingTalk 401 semantics** — confirm the 401 is genuinely the token-expiry signal (not a permission error) before wiring invalidate-on-401, to avoid redundant refetch storms (the single-flight lock already prevents thundering herd).

## Definition of Done

- WS1: docs tracked, plan closed as merged, `git status` clean, no code change.
- WS2: all 6 dependabot PRs merged, backend + frontend gates green, auth smoke test on better-auth bump, next-config rewrite tests still 6/6.
- WS3: rollback unit tests green; no regression in full backend suite.
- WS4: DingTalk + WeCom 401-refetch tests green with `invalidate()` invoked.
- WS5: 4 onboarding spec docs written; issues re-tagged and spec-linked.