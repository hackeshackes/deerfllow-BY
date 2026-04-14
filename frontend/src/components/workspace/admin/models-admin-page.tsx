"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { Model } from "@/core/models/types";

import { AdminPageShell } from "./admin-page-shell";

type FormState = {
  originalName?: string;
  name: string;
  display_name: string;
  description: string;
  use: string;
  model: string;
  base_url: string;
  api_key: string;
  temperature: string;
  supports_thinking: boolean;
  supports_reasoning_effort: boolean;
  supports_vision: boolean;
  enabled: boolean;
  is_default: boolean;
};

const emptyForm: FormState = {
  name: "",
  display_name: "",
  description: "",
  use: "deerflow.models.patched_openai:PatchedChatOpenAI",
  model: "",
  base_url: "",
  api_key: "",
  temperature: "1",
  supports_thinking: false,
  supports_reasoning_effort: false,
  supports_vision: false,
  enabled: true,
  is_default: false,
};

const presetOptions = {
  openai: {
    use: "deerflow.models.patched_openai:PatchedChatOpenAI",
    base_url: "https://api.openai.com/v1",
  },
  minimax: {
    use: "deerflow.models.patched_minimax:PatchedChatMiniMax",
    base_url: "https://api.minimaxi.com/v1",
  },
  anthropic: {
    use: "langchain_anthropic.ChatAnthropic",
    base_url: "",
  },
};

export function ModelsAdminPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);

  async function loadData() {
    const response = await fetch("/api/admin/models");
    if (!response.ok) {
      setError("加载模型配置失败");
      return;
    }
    const payload = (await response.json()) as { models: Model[] };
    setModels(payload.models);
    setError(null);
  }

  useEffect(() => {
    void loadData();
  }, []);

  const sortedModels = useMemo(() => models.slice().sort((a, b) => Number(Boolean(b.is_default)) - Number(Boolean(a.is_default))), [models]);

  function openCreateDialog() {
    setForm(emptyForm);
    setDialogOpen(true);
  }

  function openEditDialog(model: Model) {
    setForm({
      originalName: model.name,
      name: model.name,
      display_name: model.display_name ?? "",
      description: model.description ?? "",
      use: model.use ?? "",
      model: model.model,
      base_url: model.base_url ?? "",
      api_key: model.api_key ?? "",
      temperature: String(model.temperature ?? 1),
      supports_thinking: Boolean(model.supports_thinking),
      supports_reasoning_effort: Boolean(model.supports_reasoning_effort),
      supports_vision: Boolean(model.supports_vision),
      enabled: Boolean(model.enabled ?? true),
      is_default: Boolean(model.is_default),
    });
    setDialogOpen(true);
  }

  async function saveModel() {
    setError(null);
    setStatusMessage(null);
    const target = form.originalName ? `/api/admin/models/${form.originalName}` : "/api/admin/models";
    const method = form.originalName ? "PATCH" : "POST";
    const response = await fetch(target, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        temperature: Number(form.temperature),
      }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? "保存模型失败");
      return;
    }
    setDialogOpen(false);
    setStatusMessage(form.originalName ? "模型修改已保存" : "模型已创建");
    await loadData();
  }

  async function testModel(name: string) {
    setError(null);
    setStatusMessage(null);
    setTestResult(null);
    const response = await fetch(`/api/admin/models/${name}/test`, { method: "POST" });
    const payload = (await response.json()) as { ok: boolean; message: string };
    setTestResult(`${name}: ${payload.ok ? "成功" : "失败"} - ${payload.message}`);
  }

  async function reloadModels(name: string) {
    setError(null);
    setStatusMessage(null);
    await fetch(`/api/admin/models/${name}/reload`, { method: "POST" });
    setStatusMessage(`已重载 ${name} 的模型配置`);
    await loadData();
  }

  async function deleteModel(name: string) {
    setError(null);
    setStatusMessage(null);
    const confirmed = window.confirm(`确认删除模型 ${name} 吗？删除后将从管理台列表中移除。`);
    if (!confirmed) {
      return;
    }

    const response = await fetch(`/api/admin/models/${name}`, { method: "DELETE" });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? "删除模型失败");
      return;
    }

    setStatusMessage(`模型 ${name} 已删除`);
    await loadData();
  }

  function applyPreset(preset: keyof typeof presetOptions) {
    const config = presetOptions[preset];
    setForm((current) => ({ ...current, use: config.use, base_url: config.base_url }));
  }

  return (
    <AdminPageShell title="模型管理" description="通过图形界面管理系统模型配置、启停状态、默认模型与连接测试。">
      <Card>
        <CardHeader>
          <CardTitle>模型管理中心</CardTitle>
          <CardDescription>通过图形界面管理系统模型配置、启停状态、默认模型与连接测试。</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <div className="text-muted-foreground text-sm">支持 OpenAI 兼容、MiniMax 中国区、Anthropic 等模型接入。</div>
          <Button onClick={openCreateDialog}>新增模型</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>已配置模型</CardTitle>
          <CardDescription>管理员可修改启用状态、设为默认模型，并测试连接是否正常。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {sortedModels.map((model) => (
            <div key={model.name} className="rounded-2xl border px-4 py-4">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{model.display_name ?? model.name}</span>
                    {model.is_default && <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">默认</span>}
                    {model.enabled === false && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">已禁用</span>}
                  </div>
                  <div className="text-muted-foreground text-sm">内部名称：{model.name}</div>
                  <div className="text-muted-foreground text-sm">模型标识：{model.model}</div>
                  <div className="text-muted-foreground text-sm">Provider：{model.use}</div>
                  <div className="text-muted-foreground text-sm">Base URL：{model.base_url ?? "—"}</div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => openEditDialog(model)}>编辑</Button>
                  <Button variant="outline" size="sm" onClick={() => void testModel(model.name)}>测试连接</Button>
                  <Button variant="outline" size="sm" onClick={() => void reloadModels(model.name)}>重载配置</Button>
                  <Button variant="destructive" size="sm" onClick={() => void deleteModel(model.name)}>删除</Button>
                </div>
              </div>
            </div>
          ))}
          {error && <p className="text-sm text-rose-600">{error}</p>}
          {statusMessage && <p className="text-sm text-emerald-700">{statusMessage}</p>}
          {testResult && <p className="text-sm text-sky-700">{testResult}</p>}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{form.originalName ? "编辑模型" : "新增模型"}</DialogTitle>
            <DialogDescription>推荐先选择模型模板，再填写模型名称、接口地址和认证信息。</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2 md:col-span-2">
              <div className="text-sm font-medium">快速模板</div>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => applyPreset("openai")}>OpenAI Compatible</Button>
                <Button type="button" variant="outline" size="sm" onClick={() => applyPreset("minimax")}>MiniMax 中国区</Button>
                <Button type="button" variant="outline" size="sm" onClick={() => applyPreset("anthropic")}>Anthropic</Button>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium">内部名称</div>
              <Input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="例如 minimax-m2.7" />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">显示名称</div>
              <Input value={form.display_name} onChange={(event) => setForm((current) => ({ ...current, display_name: event.target.value }))} placeholder="例如 MiniMax M2.7" />
            </div>
            <div className="space-y-2 md:col-span-2">
              <div className="text-sm font-medium">描述</div>
              <Textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="该模型适合什么场景" />
            </div>
            <div className="space-y-2 md:col-span-2">
              <div className="text-sm font-medium">Provider 路径</div>
              <Input value={form.use} onChange={(event) => setForm((current) => ({ ...current, use: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">模型标识</div>
              <Input value={form.model} onChange={(event) => setForm((current) => ({ ...current, model: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">温度</div>
              <Input value={form.temperature} onChange={(event) => setForm((current) => ({ ...current, temperature: event.target.value }))} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <div className="text-sm font-medium">Base URL</div>
              <Input value={form.base_url} onChange={(event) => setForm((current) => ({ ...current, base_url: event.target.value }))} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <div className="text-sm font-medium">API Key / 环境变量</div>
              <Input value={form.api_key} onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))} placeholder="可直接填 key，或填写 $ENV_VAR" />
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">启用模型</span>
                <Switch checked={form.enabled} onCheckedChange={(checked) => setForm((current) => ({ ...current, enabled: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">设为默认模型</span>
                <Switch checked={form.is_default} onCheckedChange={(checked) => setForm((current) => ({ ...current, is_default: checked }))} />
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">支持视觉</span>
                <Switch checked={form.supports_vision} onCheckedChange={(checked) => setForm((current) => ({ ...current, supports_vision: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">支持 thinking</span>
                <Switch checked={form.supports_thinking} onCheckedChange={(checked) => setForm((current) => ({ ...current, supports_thinking: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">支持 reasoning effort</span>
                <Switch checked={form.supports_reasoning_effort} onCheckedChange={(checked) => setForm((current) => ({ ...current, supports_reasoning_effort: checked }))} />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={() => void saveModel()}>保存模型</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}
