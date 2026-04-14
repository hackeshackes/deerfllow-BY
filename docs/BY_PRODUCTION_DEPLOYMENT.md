# MicX Production Deployment

## 1. Required environment variables

Set these in the root `.env` used by `docker/docker-compose.yaml`:

```env
BETTER_AUTH_SECRET=<32+ char random secret>
BETTER_AUTH_BASE_URL=https://by.example.com
BY_ADMIN_EMAIL=sabar.bao@me.com
BY_ADMIN_PASSWORD=<strong password>
BY_ADMIN_NAME=MicX Owner

DEER_FLOW_HOME=/data/deer-flow
DEER_FLOW_HOST_BASE_DIR=/data/deer-flow
DEER_FLOW_REPO_ROOT=/opt/by/deer-flow
```

Also set your normal model/runtime secrets in `.env` as required by the backend.

## 2. Persistent storage

Create and persist the MicX runtime directory on the host:

```bash
sudo mkdir -p /data/deer-flow
sudo chown -R "$USER" /data/deer-flow
```

This directory stores:

- `users.json`
- `users/<user_id>/memory.json`
- `users/<user_id>/agents/...`
- `users/<user_id>/threads/...`

## 3. Build and start

From the repository root:

```bash
docker compose -f docker/docker-compose.yaml up -d --build
```

## 4. Smoke checks

Verify:

```bash
curl http://localhost:2026/health
```

Then open:

- `/`
- `/sign-in`

## 5. Launch validation checklist

### Chinese UX

- `/sign-in` and `/activate` render Chinese-first copy
- `/workspace/account` explains personal vs shared workspace boundaries in Chinese
- `/workspace/admin/users` and `/workspace/admin/workspaces` render Chinese management UX

### Authentication

- Owner can sign in
- Owner can sign out
- Unauthenticated access to `/workspace` redirects to `/sign-in`

### User management

- Owner can open `/workspace/admin/users`
- Owner can create an invited member
- Owner can copy an activation link for the invited member
- Invited users can activate via `/activate?token=...`
- Owner can disable/enable a member

### Isolation

Validate with at least 2 accounts:

- Threads are isolated
- Uploads are isolated
- Artifacts are isolated
- Memory is isolated
- Custom agents are isolated

### Product behavior

- Create chat
- Send message
- Upload file
- Generate artifact
- Edit memory
- Create custom agent

## 6. Rollback

Do not delete `/data/deer-flow`.

Rollback by restoring the previous image or git revision and restarting compose:

```bash
docker compose -f docker/docker-compose.yaml up -d --build
```

Re-run the smoke checks after rollback.

## 7. Notes

- Use HTTPS in front of nginx for production.
- `BETTER_AUTH_BASE_URL` should match the public origin.
- The gateway now handles `/api/session/*` and `/api/users/*` behind nginx.
