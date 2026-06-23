-- OIDC Providers
CREATE TABLE IF NOT EXISTS oidc_providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    issuer_url TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret_encrypted TEXT NOT NULL,
    discovery_url TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- RBAC v2: Roles
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    scope TEXT NOT NULL CHECK (scope IN ('system', 'department', 'project')),
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- RBAC v2: Role bindings (user/role/scope)
CREATE TABLE IF NOT EXISTS role_bindings (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    scope_id TEXT,  -- department_id or project_id, NULL for system
    granted_by TEXT,
    granted_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, role_id, scope_id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Audit Events (append-only)
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
    actor_id TEXT NOT NULL,
    actor_type TEXT NOT NULL,  -- user / system / automation / channel
    action TEXT NOT NULL,       -- e.g. "thread.create", "skill.enable"
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    workspace_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    metadata_json TEXT,         -- JSON blob
    success INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_audit_actor_time ON audit_events(actor_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action_time ON audit_events(action, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_workspace_time ON audit_events(workspace_id, occurred_at DESC);

-- SCIM Sync State
CREATE TABLE IF NOT EXISTS scim_sync_state (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL UNIQUE,
    last_sync_at TEXT,
    last_sync_status TEXT,  -- success / failed / in_progress
    last_sync_error TEXT,
    users_synced INTEGER DEFAULT 0,
    groups_synced INTEGER DEFAULT 0,
    FOREIGN KEY (provider_id) REFERENCES oidc_providers(id)
);
