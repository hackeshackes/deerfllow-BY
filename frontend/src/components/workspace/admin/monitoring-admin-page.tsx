"use client";

import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { AdminPageShell } from "./admin-page-shell";

type MonitoringPayload = {
  health: Record<string, string | boolean | string[]>;
  metrics: Record<string, number | boolean>;
  recent_audit: Array<{ ts?: string; action?: string; target?: string }>;
};

export function MonitoringAdminPage() {
  const [data, setData] = useState<MonitoringPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/admin/monitoring/overview");
        if (!response.ok) throw new Error("加载监控数据失败");
        setData((await response.json()) as MonitoringPayload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载监控数据失败");
      }
    }
    void load();
  }, []);

  return (
    <AdminPageShell title="监控中心" description="查看系统健康、关键指标和最近管理活动。">
      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>健康状态</CardTitle>
            <CardDescription>基础运行组件状态。</CardDescription>
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
            <CardTitle>关键指标</CardTitle>
            <CardDescription>用于快速判断系统规模和活跃度。</CardDescription>
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
          <CardTitle>最近审计日志</CardTitle>
          <CardDescription>便于定位最近的后台变更动作。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {(data?.recent_audit ?? []).length === 0 ? (
            <p className="text-sm text-slate-500">暂无审计日志。</p>
          ) : (
            data?.recent_audit.map((item, index) => (
              <div key={`${item.ts ?? index}-${item.action ?? index}`} className="rounded-2xl border px-4 py-3 text-sm">
                <div className="font-medium">{item.action ?? "未知动作"}</div>
                <div className="mt-1 text-slate-500">目标：{item.target ?? "—"}</div>
                <div className="mt-1 text-slate-400">{item.ts ? new Date(item.ts).toLocaleString() : "—"}</div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </AdminPageShell>
  );
}
