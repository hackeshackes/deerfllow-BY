"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

import { AdminPageShell } from "./admin-page-shell";

type AdminConfig = {
  system: { log_level?: string | null; token_usage_enabled?: boolean | null };
  tracing: {
    langsmith: { enabled?: boolean; api_key?: string | null; project?: string | null; endpoint?: string | null };
    langfuse: { enabled?: boolean; public_key?: string | null; secret_key?: string | null; host?: string | null };
  };
  branding: {
    name: string;
    short_name: string;
    tagline: string;
    description: string;
    support_email: string;
    website_path: string;
    docs_path: string;
  };
};

export function ConfigAdminPage() {
  const [form, setForm] = useState<AdminConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/admin/config");
        if (!response.ok) throw new Error("加载配置失败");
        setForm((await response.json()) as AdminConfig);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载配置失败");
      }
    }
    void load();
  }, []);

  async function save() {
    if (!form) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch("/api/admin/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? "保存配置失败");
      }
      setForm((await response.json()) as AdminConfig);
      setMessage("系统配置已保存。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存配置失败");
    } finally {
      setSaving(false);
    }
  }

  if (!form) {
    return (
      <AdminPageShell title="配置中心" description="集中管理 MicX 的系统级配置、追踪配置和品牌配置。">
        <p className="text-sm text-slate-500">正在加载配置...</p>
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="配置中心" description="支持 owner 在后台统一管理系统配置、Tracing 密钥及 MicX 品牌信息。">
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>系统配置</CardTitle>
            <CardDescription>控制日志等级和 Token 用量统计。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="text-sm font-medium">日志等级</div>
              <Input value={form.system.log_level ?? ""} onChange={(event) => setForm((current) => current ? { ...current, system: { ...current.system, log_level: event.target.value } } : current)} />
            </div>
            <div className="flex items-center justify-between rounded-2xl border px-4 py-3">
              <div>
                <div className="font-medium">启用 Token Usage</div>
                <div className="text-sm text-slate-500">用于记录模型调用的 token 使用情况。</div>
              </div>
              <Switch checked={Boolean(form.system.token_usage_enabled)} onCheckedChange={(checked) => setForm((current) => current ? { ...current, system: { ...current.system, token_usage_enabled: checked } } : current)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>MicX 品牌配置</CardTitle>
            <CardDescription>配置产品名称、简介和联系信息。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-sm font-medium">产品名称</div>
              <Input value={form.branding.name} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, name: event.target.value } } : current)} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">短名称</div>
              <Input value={form.branding.short_name} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, short_name: event.target.value } } : current)} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <div className="text-sm font-medium">Tagline</div>
              <Input value={form.branding.tagline} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, tagline: event.target.value } } : current)} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <div className="text-sm font-medium">产品描述</div>
              <Textarea value={form.branding.description} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, description: event.target.value } } : current)} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">支持邮箱</div>
              <Input value={form.branding.support_email} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, support_email: event.target.value } } : current)} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">官网路径</div>
              <Input value={form.branding.website_path} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, website_path: event.target.value } } : current)} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <div className="text-sm font-medium">文档路径</div>
              <Input value={form.branding.docs_path} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, docs_path: event.target.value } } : current)} />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Tracing 配置</CardTitle>
          <CardDescription>配置 LangSmith / Langfuse 的启用状态与连接参数。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-4 rounded-3xl border p-4">
            <div className="flex items-center justify-between">
              <div className="font-medium">LangSmith</div>
              <Switch checked={Boolean(form.tracing.langsmith.enabled)} onCheckedChange={(checked) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langsmith: { ...current.tracing.langsmith, enabled: checked } } } : current)} />
            </div>
            <Input value={form.tracing.langsmith.project ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langsmith: { ...current.tracing.langsmith, project: event.target.value } } } : current)} placeholder="Project" />
            <Input value={form.tracing.langsmith.endpoint ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langsmith: { ...current.tracing.langsmith, endpoint: event.target.value } } } : current)} placeholder="Endpoint" />
            <Input value={form.tracing.langsmith.api_key ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langsmith: { ...current.tracing.langsmith, api_key: event.target.value } } } : current)} placeholder="API Key / $ENV_VAR" />
          </div>

          <div className="space-y-4 rounded-3xl border p-4">
            <div className="flex items-center justify-between">
              <div className="font-medium">Langfuse</div>
              <Switch checked={Boolean(form.tracing.langfuse.enabled)} onCheckedChange={(checked) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langfuse: { ...current.tracing.langfuse, enabled: checked } } } : current)} />
            </div>
            <Input value={form.tracing.langfuse.host ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langfuse: { ...current.tracing.langfuse, host: event.target.value } } } : current)} placeholder="Host" />
            <Input value={form.tracing.langfuse.public_key ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langfuse: { ...current.tracing.langfuse, public_key: event.target.value } } } : current)} placeholder="Public Key / $ENV_VAR" />
            <Input value={form.tracing.langfuse.secret_key ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langfuse: { ...current.tracing.langfuse, secret_key: event.target.value } } } : current)} placeholder="Secret Key / $ENV_VAR" />
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={() => void save()} disabled={saving}>{saving ? "保存中..." : "保存配置"}</Button>
        {message && <p className="text-sm text-emerald-600">{message}</p>}
        {error && <p className="text-sm text-rose-600">{error}</p>}
      </div>
    </AdminPageShell>
  );
}
