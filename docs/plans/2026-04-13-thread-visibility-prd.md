# MicX Thread Visibility PRD

## 1. Objective

Change thread visibility from the current workspace-shared model to a new model where threads are **private by default** and can be **explicitly shared to the current workspace**.

This change must preserve existing user expectations for historical threads while preventing accidental cross-user visibility for newly created conversations.

## 2. Product Decision

Confirmed product strategy:

- New threads default to `private`
- Users can explicitly change a thread to `workspace` visibility
- Shared threads are visible to members of the same workspace
- Private threads are visible only to the thread owner
- Admins do **not** automatically gain read access to private threads
- Historical threads should remain visible under current expectations after rollout

## 3. Current Behavior

### Backend evidence

Current ownership logic in `backend/app/gateway/ownership.py` treats a thread as accessible when:

- the record has `workspace_id`
- and the current user is a member of that workspace

This means thread visibility is currently **workspace-based**, not owner-private.

### Search/list behavior

`backend/app/gateway/routers/threads.py` filters thread search by active workspace metadata, which causes recent-thread surfaces to show threads created by other members in the same workspace.

### Artifact behavior

`backend/app/gateway/routers/artifacts.py` relies on thread access control, so artifact visibility is coupled to thread visibility.

## 4. Product Goals

### Goal A — Make new conversations private by default

Users should not expose a new conversation to workspace members unless they explicitly choose to share it.

### Goal B — Preserve collaboration intentionally

Workspace collaboration should still exist, but only for threads explicitly marked as shared.

### Goal C — Keep historical behavior safe

Existing shared-visible threads should not silently disappear after migration.

### Goal D — Keep permission semantics consistent

Thread details, artifacts, exports, history, suggestions, and state access must follow the same visibility rules.

## 5. Scope

## 5.1 In scope

1. Thread metadata schema change
2. Thread read/write permission split
3. Thread list/search visibility updates
4. Explicit share/unshare API
5. Frontend shared/private UI states
6. Artifact/export permission alignment
7. Historical thread compatibility strategy

## 5.2 Out of scope for this phase

1. Per-user ACL sharing beyond workspace-level share
2. Admin override access to private thread content
3. Full channel/IM identity remapping
4. Thread-level audit browsing UI for admins

## 6. Permission Model

### 6.1 Metadata fields

Keep existing fields:

- `owner_user_id`
- `workspace_id`
- `created_by_user_id`

Add:

- `visibility: "private" | "workspace"`
- `shared_by_user_id` (optional)
- `shared_at` (optional)

### 6.2 Read rules

#### Private thread
- owner can read
- non-owner workspace members cannot read
- admins cannot read by default

#### Workspace-shared thread
- owner can read
- workspace members can read

### 6.3 Manage rules

Only owner can:

- rename thread
- delete thread
- update visibility
- modify thread state through owner-managed flows

Workspace members with read access do **not** automatically gain manage access.

## 7. Migration Strategy

### 7.1 Historical threads

Historical threads that have no explicit visibility value should be treated as:

- `visibility = workspace`

Reason:

- current behavior already exposes them to workspace members
- migrating them to `private` would cause existing conversations to disappear unexpectedly

### 7.2 Recommended migration mode

Use **lazy migration**:

- when reading a thread with no `visibility`, treat it as `workspace`
- when syncing or patching the thread later, persist the visibility field

This avoids risky one-shot data migration and preserves behavior safely.

## 8. Affected Surfaces

## 8.1 Backend

### Ownership core
- `backend/app/gateway/ownership.py`

### Thread endpoints
- `backend/app/gateway/routers/threads.py`

### Artifact access
- `backend/app/gateway/routers/artifacts.py`

### Other thread-adjacent behavior
- suggestions
- export
- thread state/history
- thread sync
- any endpoint currently calling `require_thread_owner`

## 8.2 Frontend

### Thread list / recent chats
- workspace recent conversation UI
- thread search/list surfaces

### Thread detail page
- `frontend/src/app/workspace/chats/[thread_id]/page.tsx`

### Share controls
- current share/copy-link affordances must become real visibility controls

### Artifact/export UI
- must respect shared/private state consistently

## 9. API Changes

## 9.1 New API

Add a dedicated visibility update endpoint:

`PATCH /api/threads/{thread_id}/visibility`

Request body:

```json
{
  "visibility": "private"
}
```

or

```json
{
  "visibility": "workspace"
}
```

### Requirements

- owner-only
- update store metadata
- update checkpoint metadata
- persist share audit fields when sharing occurs

## 9.2 Existing API behavior changes

### Search/list
Return:

- owner's private threads
- owner's shared threads
- workspace-shared threads created by others in the active workspace

### Get thread / history / state / artifacts
Use read access rules instead of current workspace-wide permissive logic.

### Patch/delete/state update
Use manage access rules.

## 10. Frontend UX Changes

## 10.1 Thread visibility indicator

Each thread should display one of:

- `私有`
- `已共享`

## 10.2 Share controls

Replace the current copy-only share behavior with:

- 分享到工作区
- 取消共享
- 复制链接（仅在已共享时仍然有明确意义）

## 10.3 No-access behavior

If a user opens a private thread they do not own:

- show not found / no access state
- do not leak metadata or artifacts

## 11. Channel / IM Special Handling

Channel-created threads should **not** be switched blindly to private-by-default in this phase.

Reason:

- channel identity is not yet fully mapped to authenticated user/workspace ownership semantics
- changing this without a dedicated mapping model could break IM thread access

Recommended handling for this phase:

- keep current behavior for channel-driven threads
- defer a separate channel-visibility design to a later phase

## 12. Acceptance Criteria

1. New thread defaults to `private`
2. Owner sees their private thread in recent chats
3. Other members in the same workspace do not see that private thread
4. Owner can explicitly share a thread to workspace
5. Shared thread appears for other workspace members
6. Shared thread can be unshared and disappears for others
7. Artifacts of private threads are not downloadable by non-owners
8. Artifacts of shared threads are accessible to workspace members
9. Historical threads remain visible after migration according to prior behavior
10. No thread API bypass remains that exposes private thread content through alternate endpoints

## 13. Risks

### Risk A — Hidden historical threads

If missing-visibility threads default to `private`, users will think conversations disappeared.

### Risk B — Incomplete enforcement

If one thread-adjacent endpoint keeps the old permission logic, users may still access private content indirectly.

### Risk C — Artifact leakage

If artifact routes are not aligned, private threads could still leak files.

### Risk D — Channel regressions

Blindly applying web thread semantics to channel-created threads may break channel flows.

## 14. Release Strategy

1. Implement backend permission split
2. Add visibility API
3. Update search/list semantics
4. Align artifact/export permissions
5. Add frontend share/unshare UI
6. Validate role-based visibility flows
7. Stage rollout with historical-thread compatibility
