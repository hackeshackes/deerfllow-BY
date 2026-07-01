-- v1.5.8 multitenancy + comments schema
-- Idempotent — safe to run multiple times.

CREATE TABLE IF NOT EXISTS workspaces (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    owner_email TEXT NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'free',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_memberships (
    workspace_id TEXT NOT NULL,
    user_email   TEXT NOT NULL,
    role         TEXT NOT NULL DEFAULT 'member',
    joined_at    TEXT NOT NULL,
    PRIMARY KEY (workspace_id, user_email),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS comments (
    id         TEXT PRIMARY KEY,
    thread_id  TEXT NOT NULL,
    author_id  TEXT NOT NULL,
    body       TEXT NOT NULL,
    parent_id  TEXT,
    source     TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comments_thread ON comments(thread_id);

CREATE TABLE IF NOT EXISTS resource_quotas (
    workspace_id TEXT NOT NULL,
    scope        TEXT NOT NULL,           -- 'tokens' | 'rpm' | etc.
    limit_value  INTEGER NOT NULL,
    period       TEXT NOT NULL DEFAULT 'monthly',
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (workspace_id, scope, period)
);
