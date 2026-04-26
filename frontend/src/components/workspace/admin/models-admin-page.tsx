"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { modelPresets, providers, type ModelPreset } from "@/core/config/model-presets";
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
  request_timeout: number;
  max_retries: number;
  max_tokens: number;
  temperature: string;
  supports_thinking: boolean;
  supports_reasoning_effort: boolean;
  supports_vision: boolean;
  use_responses_api: boolean;
  output_version: string;
  thinking: string;
  when_thinking_enabled: string;
  enabled: boolean;
  is_default: boolean;
  capabilities: string[];
};

const emptyForm: FormState = {
  name: "",
  display_name: "",
  description: "",
  use: "langchain_openai:ChatOpenAI",
  model: "",
  base_url: "",
  api_key: "",
  request_timeout: 120,
  max_retries: 3,
  max_tokens: 8192,
  temperature: "0.7",
  supports_thinking: false,
  supports_reasoning_effort: false,
  supports_vision: false,
  use_responses_api: false,
  output_version: "",
  thinking: "",
  when_thinking_enabled: "",
  enabled: true,
  is_default: false,
  capabilities: ["text"],
};

export function ModelsAdminPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [presetOpen, setPresetOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<string>("");
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

  const sortedModels = useMemo(
    () => models.slice().sort((a, b) => Number(Boolean(b.is_default)) - Number(Boolean(a.is_default))),
    [models],
  );

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
      request_timeout: model.request_timeout ?? 120,
      max_retries: model.max_retries ?? 3,
      max_tokens: model.max_tokens ?? 8192,
      temperature: String(model.temperature ?? 0.7),
      supports_thinking: Boolean(model.supports_thinking),
      supports_reasoning_effort: Boolean(model.supports_reasoning_effort),
      supports_vision: Boolean(model.supports_vision),
      use_responses_api: Boolean(model.use_responses_api),
      output_version: model.output_version ?? "",
      thinking: model.thinking ? JSON.stringify(model.thinking, null, 2) : "",
      when_thinking_enabled: model.when_thinking_enabled ? JSON.stringify(model.when_thinking_enabled, null, 2) : "",
      enabled: Boolean(model.enabled ?? true),
      is_default: Boolean(model.is_default),
      capabilities: model.capabilities ?? ["text"],
    });
    setDialogOpen(true);
  }

  async function saveModel() {
    setError(null);
    setStatusMessage(null);
    const payload = {
      ...form,
      temperature: Number(form.temperature),
      thinking: form.thinking ? JSON.parse(form.thinking) : null,
      when_thinking_enabled: form.when_thinking_enabled ? JSON.parse(form.when_thinking_enabled) : null,
    };
    const target = form.originalName ? `/api/admin/models/${form.originalName}` : "/api/admin/models";
    const method = form.originalName ? "PATCH" : "POST";
    const response = await fetch(target, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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

  function importPreset(preset: ModelPreset) {
    setForm({
      originalName: undefined,
      name: preset.name,
      display_name: preset.display_name,
      description: preset.description,
      use: preset.provider.toLowerCase().replace(".", "").replace(" ", "_") + ":ChatOpenAI",
      model: preset.model,
      base_url: preset.api_base,
      api_key: "",
      request_timeout: 120,
      max_retries: 3,
      max_tokens: 8192,
      temperature: "0.7",
      supports_thinking: preset.supports_thinking,
      supports_reasoning_effort: preset.supports_reasoning_effort,
      supports_vision: preset.supports_vision,
      use_responses_api: preset.use_responses_api,
      output_version: preset.output_version ?? "",
      thinking: preset.thinking ? JSON.stringify(preset.thinking, null, 2) : "",
      when_thinking_enabled: preset.when_thinking_enabled ? JSON.stringify(preset.when_thinking_enabled, null, 2) : "",
      enabled: true,
      is_default: models.length === 0,
      capabilities: ["text"],
    });
    setPresetOpen(false);
    setDialogOpen(true);
  }

  function applyJson(field: "thinking" | "when_thinking_enabled", value: string) {
    try {
      JSON.parse(value);
      setForm((current) => ({ ...current, [field]: value }));
    } catch {
      // invalid JSON, don't update
    }
  }

  return (
    <AdminPageShell title="模型管理" description="通过图形界面管理系统模型配置、启停状态、默认模型与连接测试。">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>模型管理中心</CardTitle>
              <CardDescription>支持 OpenAI 兼容、MiniMax 中国区、Anthropic 等模型接入。</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setPresetOpen(true)}>导入预设</Button>
              <Button onClick={openCreateDialog}>新增模型</Button>
            </div>
          </div>
        </CardHeader>
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
                  <div className="flex gap-2">
                    {model.supports_vision && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Vision</span>}
                    {model.supports_thinking && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Thinking</span>}
                    {model.supports_reasoning_effort && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Reasoning</span>}
                    {model.capabilities?.map((cap) => (
                      <span key={cap} className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">{cap}</span>
                    ))}
                  </div>
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
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{form.originalName ? "编辑模型" : "新增模型"}</DialogTitle>
            <DialogDescription>填写模型配置信息，或从预设模板中选择。</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <div className="text-sm font-medium">内部名称</div>
              <Input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="例如 minimax-m2" />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">显示名称</div>
              <Input value={form.display_name} onChange={(event) => setForm((current) => ({ ...current, display_name: event.target.value }))} placeholder="例如 MiniMax M2" />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">模型标识</div>
              <Input value={form.model} onChange={(event) => setForm((current) => ({ ...current, model: event.target.value }))} placeholder="例如 gpt-4o" />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">描述</div>
              <Textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="该模型适合什么场景" rows={2} />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">Provider 路径</div>
              <Input value={form.use} onChange={(event) => setForm((current) => ({ ...current, use: event.target.value }))} />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">Base URL</div>
              <Input value={form.base_url} onChange={(event) => setForm((current) => ({ ...current, base_url: event.target.value }))} placeholder="https://api.openai.com/v1" />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">API Key / 环境变量</div>
              <Input value={form.api_key} onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))} placeholder="可直接填 key，或填写 $ENV_VAR" />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">请求超时 (秒)</div>
              <Input type="number" value={form.request_timeout} onChange={(event) => setForm((current) => ({ ...current, request_timeout: Number(event.target.value) }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">最大重试次数</div>
              <Input type="number" value={form.max_retries} onChange={(event) => setForm((current) => ({ ...current, max_retries: Number(event.target.value) }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">最大 Tokens</div>
              <Input type="number" value={form.max_tokens} onChange={(event) => setForm((current) => ({ ...current, max_tokens: Number(event.target.value) }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">温度</div>
              <Input value={form.temperature} onChange={(event) => setForm((current) => ({ ...current, temperature: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">Output Version</div>
              <Input value={form.output_version} onChange={(event) => setForm((current) => ({ ...current, output_version: event.target.value }))} placeholder="responses/v1" />
            </div>

            <div className="space-y-3 md:col-span-1">
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">启用模型</span>
                <Switch checked={form.enabled} onCheckedChange={(checked) => setForm((current) => ({ ...current, enabled: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">设为默认</span>
                <Switch checked={form.is_default} onCheckedChange={(checked) => setForm((current) => ({ ...current, is_default: checked }))} />
              </div>
            </div>
            <div className="space-y-3 md:col-span-1">
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">支持视觉</span>
                <Switch checked={form.supports_vision} onCheckedChange={(checked) => setForm((current) => ({ ...current, supports_vision: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">支持 Thinking</span>
                <Switch checked={form.supports_thinking} onCheckedChange={(checked) => setForm((current) => ({ ...current, supports_thinking: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">支持 Reasoning Effort</span>
                <Switch checked={form.supports_reasoning_effort} onCheckedChange={(checked) => setForm((current) => ({ ...current, supports_reasoning_effort: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">Responses API</span>
                <Switch checked={form.use_responses_api} onCheckedChange={(checked) => setForm((current) => ({ ...current, use_responses_api: checked }))} />
              </div>
            </div>

            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">Thinking 配置 (JSON)</div>
              <Textarea
                value={form.thinking}
                onChange={(event) => applyJson("thinking", event.target.value)}
                placeholder='{"type": "thinking", ...}'
                rows={3}
              />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">When Thinking Enabled (JSON)</div>
              <Textarea
                value={form.when_thinking_enabled}
                onChange={(event) => applyJson("when_thinking_enabled", event.target.value)}
                placeholder='{"type": "enabled", ...}'
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={() => void saveModel()}>保存模型</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={presetOpen} onOpenChange={setPresetOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>导入模型预设</DialogTitle>
            <DialogDescription>选择要导入的模型预设配置。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button variant={selectedProvider === "" ? "default" : "outline"} size="sm" onClick={() => setSelectedProvider("")}>
                全部
              </Button>
              {providers.map((p) => (
                <Button key={p} variant={selectedProvider === p ? "default" : "outline"} size="sm" onClick={() => setSelectedProvider(p)}>
                  {p}
                </Button>
              ))}
            </div>
            <div className="grid gap-3">
              {modelPresets
                .filter((p) => selectedProvider === "" || p.provider === selectedProvider)
                .map((preset) => (
                  <div
                    key={preset.name}
                    className="flex items-center justify-between rounded-2xl border p-4 cursor-pointer hover:bg-slate-50"
                    onClick={() => importPreset(preset)}
                  >
                    <div>
                      <div className="font-medium">{preset.display_name}</div>
                      <div className="text-sm text-slate-500">{preset.description}</div>
                      <div className="mt-1 flex gap-2">
                        <span className="text-xs text-slate-400">{preset.provider}</span>
                        <span className="text-xs text-slate-400">•</span>
                        <span className="text-xs text-slate-400">{preset.model}</span>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      {preset.supports_vision && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Vision</span>}
                      {preset.supports_thinking && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Thinking</span>}
                      {preset.supports_reasoning_effort && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Reasoning</span>}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}
