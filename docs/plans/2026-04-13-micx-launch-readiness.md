# MicX vNext Launch Readiness

## Scope Delivered

- Admin dashboard
- Admin config center
- Admin monitoring center
- Admin skills management with remote install
- Secret storage and masking for admin-managed sensitive config
- Admin audit log
- Chinese-first skill metadata editing
- MicX frontend/product-facing brand migration
- Thread visibility model: private by default, explicit workspace sharing
- Gateway-authoritative thread search, rename, visibility, and delete flows
- Personal-workspace thread privacy enforcement
- Stale thread fallback to safe new-chat route
- Admin user deletion with safety guards

## Verification Summary

### Frontend

Executed in `frontend/`:

- `npx pnpm install --frozen-lockfile`
- `npx pnpm typecheck`
- `npx pnpm lint`
- `SKIP_ENV_VALIDATION=1 BETTER_AUTH_SECRET=micx-local-secret npx pnpm build`

Status:

- TypeScript check: PASS
- ESLint: PASS
- Production build: PASS

### Backend

Executed from repository root with `PYTHONPATH="backend:backend/packages/harness"`:

- `python3 -m py_compile ...changed backend files...`
- `python3 -m pytest backend/tests/test_admin_secret_store.py backend/tests/test_admin_tracing_config.py backend/tests/test_admin_router_security.py backend/tests/test_remote_skill_install.py -q`
- `python3 -m pytest backend/tests/test_tracing_config.py -q`
- Python 3.12 containerized verification for conversation system changes:
  - `tests/test_thread_visibility.py`
  - `tests/test_artifacts_router.py`

Status:

- Changed-file syntax compile: PASS
- New targeted backend tests: PASS (`9 passed`)
- Existing tracing tests: PASS (`7 passed`)
- Thread visibility / artifact permissions backend tests: PASS (`15 passed`)

### Multi-user smoke checks

Validated locally against the running MicX stack:

- private thread is hidden from another member in the same shared workspace
- shared thread becomes visible to another member after explicit share
- thread becomes hidden again after switching back to private
- deleted thread disappears from other members' search results
- stale direct thread URL redirects to `/workspace/chats/new`

## Known Verification Constraint

Full backend suite validation is currently blocked in this shell environment because:

- local Python is `3.11`
- repository backend requires `3.12+`
- some existing code paths use Python 3.12-only features (for example `typing.override` and newer generic syntax patterns)

This means:

- the implemented MicX backend changes have targeted passing verification
- but full backend suite / full app runtime verification still needs to be re-run in the project's intended Python 3.12 environment

## Pre-Launch Checklist

Before production rollout, confirm all items below in a Python 3.12 runtime:

1. Install backend dependencies using the project's standard workflow (`uv` / workspace env)
2. Run backend targeted tests again
3. Run backend broader regression suite for routers/config/skills/auth paths
4. Start backend + frontend + nginx stack
5. Verify owner login
6. Verify `/workspace/admin`
7. Verify `/workspace/admin/config` save and reload
8. Verify `/workspace/admin/monitoring`
9. Verify `/workspace/admin/skills` remote install flow
10. Verify skill enable/disable
11. Verify skill Chinese metadata edit flow
12. Verify model management read/create/update/delete/reload/test
13. Verify user management create/invite/disable
14. Verify workspace management create/add member/view stats
15. Verify audit log visibility
16. Verify secrets are masked after save
17. Verify tracing config is effective after save
18. Run frontend build again in CI or release environment
19. Verify thread rename persists in recent list and detail view
20. Verify thread share/private toggle propagates across users in the same shared workspace
21. Verify personal-workspace threads do not expose share actions
22. Verify thread delete removes access from direct URL and recent list

## Suggested Smoke Test Plan

### Admin config

- save LangSmith project/endpoint/api key
- reopen page and confirm masked secret behavior
- confirm config remains readable and does not revert unexpectedly

### Admin monitoring

- open overview page
- confirm metrics cards render
- confirm health state and recent audit list render

### Skills

- install a remote `.skill`
- confirm installed skill shows source and metadata
- confirm default state is disabled
- enable it
- add Chinese display name and Chinese description

### Branding

- verify landing page, sign-in, activate, workspace header, about page all show `MicX`

### Conversation system

- owner creates private thread in shared workspace → member cannot see it
- owner shares thread → member can see it
- owner renames thread → member sees updated title after refresh/search
- owner sets private again → member loses access
- owner deletes thread → direct URL and recent list no longer expose it
- direct access to stale thread URL redirects to `/workspace/chats/new`

## Rollback Notes

### Frontend rollback

- rollback to previous git revision or release artifact
- rebuild frontend bundle
- redeploy frontend container/app

### Backend rollback

- rollback backend code to previous git revision or release artifact
- preserve persisted admin data under the configured runtime directory
- specifically keep:
  - admin config JSON
  - encrypted admin secrets file
  - admin audit log
  - skill metadata JSON
  - thread metadata store and checkpoint state, including `visibility` fields

### Data compatibility caution

This release introduces new admin-side persisted files. If a rollback target predates these files, the older version may ignore them safely, but this should be verified in staging first.

## Recommended Release Decision

### Current state

- Ready for staging validation
- Backend Python 3.12 validation completed for the latest conversation-system changes
- Ready for staging / pre-production rollout with the smoke checks above

### Release recommendation

1. Promote to staging
2. Complete the conversation-system smoke checks above in staging
3. Verify nginx/backend restart order in deployment automation to avoid temporary upstream drift
4. Approve production rollout after staging pass
