import type { AuditEvent, OIDCProvider, OIDCProviderCreate, Role } from "./types";

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    credentials: "include",
  });
  if (!resp.ok) {
    throw new Error(`${resp.status} ${resp.statusText}: ${await resp.text()}`);
  }
  return resp.json();
}

export const identityApi = {
  // OIDC Providers
  listProviders: () => fetchJSON<OIDCProvider[]>("/api/admin/oidc/providers"),
  createProvider: (data: OIDCProviderCreate) =>
    fetchJSON<OIDCProvider>("/api/admin/oidc/providers", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteProvider: (id: string) =>
    fetchJSON<void>(`/api/admin/oidc/providers/${id}`, { method: "DELETE" }),

  // Audit
  queryAudit: (params: {
    actor_id?: string;
    workspace_id?: string;
    action?: string;
    limit?: number;
  }) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v != null) as [string, string][],
    ).toString();
    return fetchJSON<{ events: AuditEvent[] }>(`/api/admin/audit/events?${qs}`);
  },
  exportAuditCSV: (workspace_id?: string) => {
    const qs = workspace_id ? `?workspace_id=${workspace_id}` : "";
    return fetch(`/api/admin/audit/export${qs}`, { credentials: "include" }).then((r) => r.text());
  },

  // Roles
  listRoles: () => fetchJSON<Role[]>("/api/admin/roles"),
  createRole: (data: Omit<Role, "created_at">) =>
    fetchJSON<Role>("/api/admin/roles", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteRole: (id: string) => fetchJSON<void>(`/api/admin/roles/${id}`, { method: "DELETE" }),
};
