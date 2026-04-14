# Thread Visibility Execution Plan

## Milestone 1 — Permission foundation

- [ ] Add `visibility` metadata support to thread ownership model
- [ ] Add owner-read vs owner-manage distinction in backend permission helpers
- [ ] Implement lazy fallback for historical threads with missing visibility
- [ ] Remove or constrain unsafe ownership fallback behavior that can infer ownership from directories alone

## Milestone 2 — Thread API enforcement

- [ ] Update thread search/list logic to return only private-owner threads plus explicitly shared workspace threads
- [ ] Update thread get/detail access to use read permissions
- [ ] Update thread history/state/sync access to use read/manage permissions appropriately
- [ ] Update delete/patch/title/state mutation flows to require manage permissions

## Milestone 3 — Explicit sharing API

- [ ] Add `PATCH /api/threads/{thread_id}/visibility`
- [ ] Persist `visibility` in store metadata
- [ ] Persist `visibility` in checkpoint metadata
- [ ] Add optional `shared_by_user_id` and `shared_at` audit fields

## Milestone 4 — Artifacts and related resources

- [ ] Align artifact preview/download with thread read permission
- [ ] Align export and thread-adjacent resource access with thread read permission
- [ ] Verify no side-channel access remains through sync/history/state APIs

## Milestone 5 — Frontend share UX

- [ ] Add private/shared badge in thread UI
- [ ] Replace copy-only sharing affordance with share/unshare action
- [ ] Add no-access handling for private threads opened by non-owners
- [ ] Ensure recent-thread list reflects backend-filtered visibility rules cleanly

## Milestone 6 — Compatibility and migration

- [ ] Treat legacy threads without `visibility` as `workspace`
- [ ] Persist visibility lazily on sync/patch/update paths
- [ ] Keep channel/IM thread handling unchanged for this phase

## Milestone 7 — Verification

- [ ] Add backend unit tests for private/shared read access
- [ ] Add backend tests for visibility update API
- [ ] Add backend tests for artifact access under private/shared threads
- [ ] Add frontend verification for private/shared badges and share controls
- [ ] Run multi-user smoke tests across owner/member/member-other-workspace scenarios
- [ ] Confirm historical thread visibility remains stable after rollout
