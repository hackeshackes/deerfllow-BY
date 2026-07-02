"use client";
import { useState } from "react";

import {
  multitenancyApi,
  type Quota,
} from "@/core/multitenancy/api";
import { useCostSummary } from "@/core/multitenancy/hooks/use-cost-summary";

export default function CostPage() {
  const [tenantId, setTenantId] = useState("default");
  const { summary, loading, error } = useCostSummary(tenantId);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [enforceMode, setEnforceMode] = useState<"advisory" | "soft" | "hard">(
    "advisory",
  );

  const reloadQuota = async () => {
    try {
      const next = await multitenancyApi.getQuota(tenantId);
      setQuota(next);
      setEnforceMode(next.enforce_mode);
    } catch (e) {
      console.error(e);
    }
  };

  const saveQuota = async () => {
    const updated = await multitenancyApi.setQuota(tenantId, {
      max_tokens: quota?.max_tokens ?? 0,
      max_rpm: quota?.max_rpm ?? 0,
      period: quota?.period ?? "monthly",
      enforce_mode: enforceMode,
    });
    setQuota(updated);
  };

  return (
    <section
      data-testid="cost-dashboard"
      className="flex flex-col gap-4 p-6"
    >
      <h1 className="text-2xl font-bold">Cost Dashboard</h1>
      <label className="flex items-center gap-2 text-sm">
        Tenant ID
        <input
          data-testid="cost-tenant-input"
          value={tenantId}
          onChange={(e) => setTenantId(e.target.value)}
          className="rounded border px-2 py-1"
        />
      </label>
      {loading && <p data-testid="cost-loading">Loading…</p>}
      {error && (
        <p data-testid="cost-error" className="text-red-600">
          {error}
        </p>
      )}
      {summary && (
        <div
          data-testid="cost-summary"
          className="flex flex-col gap-2"
        >
          <div className="text-3xl font-mono">
            {summary.total_tokens.toLocaleString()} tokens
          </div>
          <p className="text-xs text-muted-foreground">
            {summary.total_requests} requests · tenant{" "}
            {summary.tenant_id}
          </p>
          <h2 className="mt-4 text-lg font-semibold">By Model</h2>
          <ul
            data-testid="cost-breakdown"
            className="flex flex-col gap-1"
          >
            {summary.by_model.length === 0 ? (
              <li className="italic text-muted-foreground text-xs">
                No usage recorded yet
              </li>
            ) : (
              summary.by_model.map((b) => (
                <li
                  key={b.entity_id}
                  data-testid={`cost-row-${b.entity_id}`}
                  className="flex justify-between border-b py-1 text-sm"
                >
                  <span>{b.entity_id}</span>
                  <span className="font-mono">
                    {b.total_tokens.toLocaleString()} tokens ·{" "}
                    {b.request_count} req
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
      <h2 className="mt-6 text-lg font-semibold">Quota</h2>
      <button
        type="button"
        data-testid="cost-quota-reload"
        onClick={() => void reloadQuota()}
        className="rounded border px-2 py-1 text-sm"
      >
        Reload quota
      </button>
      {quota && (
        <div
          data-testid="cost-quota"
          className="flex flex-col gap-2 text-sm"
        >
          <p>Tenant: {quota.tenant_id}</p>
          <p>Token limit: {quota.max_tokens.toLocaleString()}</p>
          <p>RPM limit: {quota.max_rpm}</p>
          <p>Period: {quota.period}</p>
          <p>Mode: {quota.enforce_mode}</p>
        </div>
      )}
      <label className="flex items-center gap-2 text-sm">
        Enforce mode
        <select
          data-testid="cost-enforce-mode"
          value={enforceMode}
          onChange={(e) =>
            setEnforceMode(
              e.target.value as "advisory" | "soft" | "hard",
            )
          }
          className="rounded border px-2 py-1"
        >
          <option value="advisory">advisory</option>
          <option value="soft">soft</option>
          <option value="hard">hard</option>
        </select>
      </label>
      <button
        type="button"
        data-testid="cost-quota-save"
        onClick={() => void saveQuota()}
        className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
      >
        Save quota
      </button>
    </section>
  );
}