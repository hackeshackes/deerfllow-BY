"use client";

import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { AdminPageShell } from "./admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

type MonitoringPayload = {
  health: Record<string, string | boolean | string[]>;
  metrics: Record<string, number | boolean>;
  recent_audit: Array<{ ts?: string; action?: string; target?: string }>;
};

export function MonitoringAdminPage() {
  const { t } = useI18n();
  const [data, setData] = useState<MonitoringPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/admin/monitoring/overview");
        if (!response.ok) throw new Error(t.admin.monitoring.loadFailed);
        setData((await response.json()) as MonitoringPayload);
      } catch (err) {
        setError(err instanceof Error ? err.message : t.admin.monitoring.loadFailed);
      }
    }
    void load();
  }, [t.admin.monitoring.loadFailed]);

  return (
    <AdminPageShell title={t.admin.monitoring.title} description={t.admin.monitoring.description}>
      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t.admin.monitoring.healthStatus}</CardTitle>
            <CardDescription>{t.admin.monitoring.healthDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {Object.entries(data?.health ?? {}).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded-2xl border px-4 py-3">
                <span className="text-slate-500">{key}</span>
                <span className="font-medium">{Array.isArray(value) ? value.join(", ") || "—" : String(value)}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t.admin.monitoring.keyMetrics}</CardTitle>
            <CardDescription>{t.admin.monitoring.metricsDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {Object.entries(data?.metrics ?? {}).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded-2xl border px-4 py-3">
                <span className="text-slate-500">{key}</span>
                <span className="font-medium">{String(value)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.monitoring.recentAuditLogs}</CardTitle>
          <CardDescription>{t.admin.monitoring.recentAuditLogsDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {(data?.recent_audit ?? []).length === 0 ? (
            <p className="text-sm text-slate-500">{t.admin.monitoring.noAuditLogs}</p>
          ) : (
            data?.recent_audit.map((item, index) => (
              <div key={`${item.ts ?? index}-${item.action ?? index}`} className="rounded-2xl border px-4 py-3 text-sm">
                <div className="font-medium">{item.action ?? t.admin.monitoring.unknownAction}</div>
                <div className="mt-1 text-slate-500">{t.admin.monitoring.target}：{item.target ?? "—"}</div>
                <div className="mt-1 text-slate-400">{item.ts ? new Date(item.ts).toLocaleString() : "—"}</div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </AdminPageShell>
  );
}