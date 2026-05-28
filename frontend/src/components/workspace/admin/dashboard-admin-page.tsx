"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { AdminPageShell } from "./admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

type OverviewPayload = {
  health: {
    gateway: string;
    runtime_initialized: boolean;
    checkpointer_initialized: boolean;
    store_initialized: boolean;
    tracing_enabled_providers: string[];
    tracing_explicit_providers: string[];
  };
  metrics: Record<string, number | boolean>;
  tracing: {
    langsmith?: { enabled?: boolean; configured?: boolean; project?: string | null };
    langfuse?: { enabled?: boolean; configured?: boolean; host?: string | null };
  };
  recent_audit: Array<{ ts?: string; action?: string; actor_id?: string | null; target?: string }>;
};

export function DashboardAdminPage() {
  const { t } = useI18n();
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/admin/monitoring/overview");
        if (!response.ok) throw new Error(t.admin.dashboard.loadFailed);
        setData((await response.json()) as OverviewPayload);
      } catch (err) {
        setError(err instanceof Error ? err.message : t.admin.dashboard.loadFailed);
      }
    }
    void load();
  }, [t.admin.dashboard.loadFailed]);

  const metricLabels: Record<string, string> = {
    user_count: t.admin.dashboard.userCount,
    workspace_count: t.admin.dashboard.workspaceCount,
    model_count: t.admin.dashboard.modelCount,
    skill_count: t.admin.dashboard.skillCount,
    custom_skill_count: t.admin.dashboard.customSkillCount,
    thread_count: t.admin.dashboard.threadCount,
    upload_file_count: t.admin.dashboard.uploadFileCount,
    artifact_file_count: t.admin.dashboard.artifactFileCount,
    agent_count: t.admin.dashboard.agentCount,
    run_count: t.admin.dashboard.runCount,
  };

  return (
    <AdminPageShell title={t.admin.dashboard.title} description={t.admin.dashboard.description}>
      {error && <p className="text-sm text-rose-600">{error}</p>}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Object.entries(data?.metrics ?? {})
          .filter(([key, value]) => typeof value === "number" && metricLabels[key])
          .map(([key, value]) => (
            <Card key={key}>
              <CardHeader className="pb-3">
                <CardDescription>{metricLabels[key]}</CardDescription>
                <CardTitle className="text-3xl">{value}</CardTitle>
              </CardHeader>
            </Card>
          ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader>
            <CardTitle>{t.admin.dashboard.runningHealth}</CardTitle>
            <CardDescription>{t.admin.dashboard.healthDescription}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border p-4">
              <div className="text-sm text-slate-500">{t.admin.dashboard.gateway}</div>
              <div className="mt-2 font-medium">{data?.health.gateway ?? "unknown"}</div>
            </div>
            <div className="rounded-2xl border p-4">
              <div className="text-sm text-slate-500">{t.admin.dashboard.runtime}</div>
              <div className="mt-2 font-medium">{data?.health.runtime_initialized ? t.admin.dashboard.initialized : t.admin.dashboard.notInitialized}</div>
            </div>
            <div className="rounded-2xl border p-4">
              <div className="text-sm text-slate-500">{t.admin.dashboard.checkpointer}</div>
              <div className="mt-2 font-medium">{data?.health.checkpointer_initialized ? t.admin.dashboard.ready : t.admin.dashboard.notReady}</div>
            </div>
            <div className="rounded-2xl border p-4">
              <div className="text-sm text-slate-500">{t.admin.dashboard.store}</div>
              <div className="mt-2 font-medium">{data?.health.store_initialized ? t.admin.dashboard.ready : t.admin.dashboard.notReady}</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t.admin.dashboard.tracingOverview}</CardTitle>
            <CardDescription>{t.admin.dashboard.tracingDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="rounded-2xl border p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="font-medium">LangSmith</div>
                <Badge variant={data?.tracing.langsmith?.configured ? "default" : "outline"}>{data?.tracing.langsmith?.configured ? t.admin.dashboard.configured : t.admin.dashboard.notConfigured}</Badge>
              </div>
              <div className="mt-2 text-slate-500">{t.admin.dashboard.project}：{data?.tracing.langsmith?.project ?? "—"}</div>
            </div>
            <div className="rounded-2xl border p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="font-medium">Langfuse</div>
                <Badge variant={data?.tracing.langfuse?.configured ? "default" : "outline"}>{data?.tracing.langfuse?.configured ? t.admin.dashboard.configured : t.admin.dashboard.notConfigured}</Badge>
              </div>
              <div className="mt-2 text-slate-500">{t.admin.dashboard.host}：{data?.tracing.langfuse?.host ?? "—"}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.dashboard.recentActions}</CardTitle>
          <CardDescription>{t.admin.dashboard.recentActionsDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {(data?.recent_audit ?? []).length === 0 ? (
            <p className="text-sm text-slate-500">{t.admin.dashboard.noLogs}</p>
          ) : (
            data?.recent_audit.map((item, index) => (
              <div key={`${item.ts ?? index}-${item.action ?? index}`} className="rounded-2xl border px-4 py-3 text-sm">
                <div className="font-medium">{item.action ?? t.admin.dashboard.unknownAction}</div>
                <div className="mt-1 text-slate-500">{t.admin.dashboard.actor}：{item.actor_id ?? "system"} · {t.admin.dashboard.target}：{item.target ?? "—"}</div>
                <div className="mt-1 text-slate-400">{item.ts ? new Date(item.ts).toLocaleString() : "—"}</div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </AdminPageShell>
  );
}