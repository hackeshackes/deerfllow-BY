"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { AdminPageShell } from "./admin-page-shell";

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

const metricLabels: Record<string, string> = {
  user_count: "用户数",
  workspace_count: "空间数",
  model_count: "模型数",
  skill_count: "技能数",
  custom_skill_count: "自定义技能",
  thread_count: "线程数",
  upload_file_count: "上传文件数",
  artifact_file_count: "产物数",
  agent_count: "智能体数",
  run_count: "运行数",
};

export function DashboardAdminPage() {
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/admin/monitoring/overview");
        if (!response.ok) throw new Error("加载后台总览失败");
        setData((await response.json()) as OverviewPayload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载后台总览失败");
      }
    }
    void load();
  }, []);

  return (
    <AdminPageShell title="后台总览" description="集中查看 MicX 当前运行状态、关键指标、追踪配置和最近管理动作。">
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
            <CardTitle>运行健康</CardTitle>
            <CardDescription>核心服务与运行基础状态。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border p-4">
              <div className="text-sm text-slate-500">Gateway</div>
              <div className="mt-2 font-medium">{data?.health.gateway ?? "unknown"}</div>
            </div>
            <div className="rounded-2xl border p-4">
              <div className="text-sm text-slate-500">Runtime</div>
              <div className="mt-2 font-medium">{data?.health.runtime_initialized ? "已初始化" : "未初始化"}</div>
            </div>
            <div className="rounded-2xl border p-4">
              <div className="text-sm text-slate-500">Checkpointer</div>
              <div className="mt-2 font-medium">{data?.health.checkpointer_initialized ? "正常" : "未就绪"}</div>
            </div>
            <div className="rounded-2xl border p-4">
              <div className="text-sm text-slate-500">Store</div>
              <div className="mt-2 font-medium">{data?.health.store_initialized ? "正常" : "未就绪"}</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tracing 概览</CardTitle>
            <CardDescription>LangSmith / Langfuse 当前配置状态。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="rounded-2xl border p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="font-medium">LangSmith</div>
                <Badge variant={data?.tracing.langsmith?.configured ? "default" : "outline"}>{data?.tracing.langsmith?.configured ? "已配置" : "未配置"}</Badge>
              </div>
              <div className="mt-2 text-slate-500">项目：{data?.tracing.langsmith?.project ?? "—"}</div>
            </div>
            <div className="rounded-2xl border p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="font-medium">Langfuse</div>
                <Badge variant={data?.tracing.langfuse?.configured ? "default" : "outline"}>{data?.tracing.langfuse?.configured ? "已配置" : "未配置"}</Badge>
              </div>
              <div className="mt-2 text-slate-500">Host：{data?.tracing.langfuse?.host ?? "—"}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>最近管理动作</CardTitle>
          <CardDescription>用于快速确认最近的配置和后台操作。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {(data?.recent_audit ?? []).length === 0 ? (
            <p className="text-sm text-slate-500">暂无管理日志。</p>
          ) : (
            data?.recent_audit.map((item, index) => (
              <div key={`${item.ts ?? index}-${item.action ?? index}`} className="rounded-2xl border px-4 py-3 text-sm">
                <div className="font-medium">{item.action ?? "未知动作"}</div>
                <div className="mt-1 text-slate-500">操作者：{item.actor_id ?? "system"} · 目标：{item.target ?? "—"}</div>
                <div className="mt-1 text-slate-400">{item.ts ? new Date(item.ts).toLocaleString() : "—"}</div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </AdminPageShell>
  );
}
