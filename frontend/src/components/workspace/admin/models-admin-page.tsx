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
import { useI18n } from "@/core/i18n/hooks";

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
  const { t } = useI18n();
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
      setError(t.admin.models.loadFailed);
      return;
    }
    const payload = (await response.json()) as { models: Model[] };
    setModels(payload.models);
    setError(null);
  }

  useEffect(() => {
    void loadData();
  }, [t.admin.models.loadFailed]);

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
      setError(body?.detail ?? t.admin.models.loadFailed);
      return;
    }
    setDialogOpen(false);
    setStatusMessage(form.originalName ? t.admin.models.modelModifiedSaved : t.admin.models.modelCreated);
    await loadData();
  }

  async function testModel(name: string) {
    setError(null);
    setStatusMessage(null);
    setTestResult(null);
    const response = await fetch(`/api/admin/models/${name}/test`, { method: "POST" });
    const payload = (await response.json()) as { ok: boolean; message: string };
    setTestResult(`${name}: ${payload.ok ? t.admin.models.testSuccess : t.admin.models.testFailed} - ${payload.message}`);
  }

  async function reloadModels(name: string) {
    setError(null);
    setStatusMessage(null);
    await fetch(`/api/admin/models/${name}/reload`, { method: "POST" });
    setStatusMessage(`${t.admin.models.configReloaded} ${name}`);
    await loadData();
  }

  async function deleteModel(name: string) {
    setError(null);
    setStatusMessage(null);
    const confirmed = window.confirm(`${t.admin.models.deleteConfirm.replace("{name}", name)}`);
    if (!confirmed) {
      return;
    }

    const response = await fetch(`/api/admin/models/${name}`, { method: "DELETE" });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? t.admin.models.loadFailed);
      return;
    }

    setStatusMessage(t.admin.models.modelDeleted);
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
    <AdminPageShell title={t.admin.models.title} description={t.admin.models.description}>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{t.admin.models.modelCenter}</CardTitle>
              <CardDescription>{t.admin.models.modelCenterDescription}</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setPresetOpen(true)}>{t.admin.models.importPreset}</Button>
              <Button onClick={openCreateDialog}>{t.admin.models.addModel}</Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.models.configuredModels}</CardTitle>
          <CardDescription>{t.admin.models.configuredModelsDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {sortedModels.map((model) => (
            <div key={model.name} className="rounded-2xl border px-4 py-4">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{model.display_name ?? model.name}</span>
                    {model.is_default && <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">{t.admin.models.default}</span>}
                    {model.enabled === false && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{t.admin.models.disabled}</span>}
                  </div>
                  <div className="text-muted-foreground text-sm">{t.admin.models.internalName}：{model.name}</div>
                  <div className="text-muted-foreground text-sm">{t.admin.models.modelIdentifier}：{model.model}</div>
                  <div className="text-muted-foreground text-sm">{t.admin.models.provider}：{model.use}</div>
                  <div className="text-muted-foreground text-sm">{t.admin.models.baseUrl}：{model.base_url ?? "—"}</div>
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
                  <Button variant="outline" size="sm" onClick={() => openEditDialog(model)}>{t.admin.models.editModel}</Button>
                  <Button variant="outline" size="sm" onClick={() => void testModel(model.name)}>{t.admin.models.testConnection}</Button>
                  <Button variant="outline" size="sm" onClick={() => void reloadModels(model.name)}>{t.admin.models.reloadConfig}</Button>
                  <Button variant="destructive" size="sm" onClick={() => void deleteModel(model.name)}>{t.admin.models.delete}</Button>
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
            <DialogTitle>{form.originalName ? t.admin.models.editModel : t.admin.models.addNewModel}</DialogTitle>
            <DialogDescription>{t.admin.models.modelDescription}</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.models.internalName}</div>
              <Input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="e.g. minimax-m2" />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.models.displayName}</div>
              <Input value={form.display_name} onChange={(event) => setForm((current) => ({ ...current, display_name: event.target.value }))} placeholder="e.g. MiniMax M2" />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.models.modelIdentifier}</div>
              <Input value={form.model} onChange={(event) => setForm((current) => ({ ...current, model: event.target.value }))} placeholder="e.g. gpt-4o" />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">{t.admin.models.modelDescription}</div>
              <Textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder={t.admin.models.modelDescription} rows={2} />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">{t.admin.models.providerPath}</div>
              <Input value={form.use} onChange={(event) => setForm((current) => ({ ...current, use: event.target.value }))} />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">{t.admin.models.baseUrl}</div>
              <Input value={form.base_url} onChange={(event) => setForm((current) => ({ ...current, base_url: event.target.value }))} placeholder="https://api.openai.com/v1" />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">{t.admin.models.apiKey}</div>
              <Input value={form.api_key} onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))} placeholder="可直接填 key，或填写 $ENV_VAR" />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.models.requestTimeout}</div>
              <Input type="number" value={form.request_timeout} onChange={(event) => setForm((current) => ({ ...current, request_timeout: Number(event.target.value) }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.models.maxRetries}</div>
              <Input type="number" value={form.max_retries} onChange={(event) => setForm((current) => ({ ...current, max_retries: Number(event.target.value) }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.models.maxTokens}</div>
              <Input type="number" value={form.max_tokens} onChange={(event) => setForm((current) => ({ ...current, max_tokens: Number(event.target.value) }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.models.temperature}</div>
              <Input value={form.temperature} onChange={(event) => setForm((current) => ({ ...current, temperature: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.models.outputVersion}</div>
              <Input value={form.output_version} onChange={(event) => setForm((current) => ({ ...current, output_version: event.target.value }))} placeholder="responses/v1" />
            </div>

            <div className="space-y-3 md:col-span-1">
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">{t.admin.models.enableModel}</span>
                <Switch checked={form.enabled} onCheckedChange={(checked) => setForm((current) => ({ ...current, enabled: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">{t.admin.models.setAsDefault}</span>
                <Switch checked={form.is_default} onCheckedChange={(checked) => setForm((current) => ({ ...current, is_default: checked }))} />
              </div>
            </div>
            <div className="space-y-3 md:col-span-1">
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">{t.admin.models.supportVision}</span>
                <Switch checked={form.supports_vision} onCheckedChange={(checked) => setForm((current) => ({ ...current, supports_vision: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">{t.admin.models.supportThinking}</span>
                <Switch checked={form.supports_thinking} onCheckedChange={(checked) => setForm((current) => ({ ...current, supports_thinking: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">{t.admin.models.supportReasoningEffort}</span>
                <Switch checked={form.supports_reasoning_effort} onCheckedChange={(checked) => setForm((current) => ({ ...current, supports_reasoning_effort: checked }))} />
              </div>
              <div className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span className="text-sm">{t.admin.models.responsesApi}</span>
                <Switch checked={form.use_responses_api} onCheckedChange={(checked) => setForm((current) => ({ ...current, use_responses_api: checked }))} />
              </div>
            </div>

            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">{t.admin.models.thinkingConfig}</div>
              <Textarea
                value={form.thinking}
                onChange={(event) => applyJson("thinking", event.target.value)}
                placeholder='{"type": "thinking", ...}'
                rows={3}
              />
            </div>
            <div className="space-y-2 md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium">{t.admin.models.whenThinkingEnabled}</div>
              <Textarea
                value={form.when_thinking_enabled}
                onChange={(event) => applyJson("when_thinking_enabled", event.target.value)}
                placeholder='{"type": "enabled", ...}'
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>{t.admin.models.cancel}</Button>
            <Button onClick={() => void saveModel()}>{t.admin.models.saveModel}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={presetOpen} onOpenChange={setPresetOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t.admin.models.importModelPreset}</DialogTitle>
            <DialogDescription>{t.admin.models.selectPreset}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button variant={selectedProvider === "" ? "default" : "outline"} size="sm" onClick={() => setSelectedProvider("")}>
                {t.admin.models.all}
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