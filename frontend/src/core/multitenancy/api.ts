export interface CostBreakdown {
  entity_id: string;
  total_tokens: number;
  request_count: number;
}

export interface UsageSummary {
  tenant_id: string;
  total_tokens: number;
  total_requests: number;
  by_tenant: CostBreakdown[];
  by_user: CostBreakdown[];
  by_model: CostBreakdown[];
}

export type QuotaPeriod = "monthly" | "daily";
export type EnforceMode = "advisory" | "soft" | "hard";

export interface Quota {
  tenant_id: string;
  max_tokens: number;
  max_rpm: number;
  period: QuotaPeriod;
  enforce_mode: EnforceMode;
}

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!resp.ok) throw new Error(`${resp.status}: ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

export const multitenancyApi = {
  costSummary: (tenantId: string) =>
    fetchJSON<UsageSummary>(
      `/api/admin/cost/summary?tenant_id=${encodeURIComponent(tenantId)}`,
    ),
  getQuota: (tenantId: string) =>
    fetchJSON<Quota>(`/api/admin/quota/${encodeURIComponent(tenantId)}`),
  setQuota: (tenantId: string, quota: Omit<Quota, "tenant_id">) =>
    fetchJSON<Quota>(`/api/admin/quota/${encodeURIComponent(tenantId)}`, {
      method: "PUT",
      body: JSON.stringify(quota),
    }),
};