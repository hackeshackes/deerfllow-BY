"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

import { AdminPageShell } from "./admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

function emitBrandUpdate(branding: AdminConfig["branding"]) {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent("micx-brand-updated", {
      detail: {
        name: branding.name,
        shortName: branding.short_name,
        tagline: branding.tagline,
        description: branding.description,
        supportEmail: branding.support_email,
        websitePath: branding.website_path,
        docsPath: branding.docs_path,
        loginBadge: branding.login_badge,
        loginTitle: branding.login_title,
        loginSubtitle: branding.login_subtitle,
        featureTitle1: branding.feature_title_1,
        featureDesc1: branding.feature_desc_1,
        featureTitle2: branding.feature_title_2,
        featureDesc2: branding.feature_desc_2,
        homepageCapabilitiesTitle: branding.homepage_capabilities_title,
        homepageCapabilitiesDesc: branding.homepage_capabilities_desc,
        homepageCapabilitiesTitle2: branding.homepage_capabilities_title_2,
        homepageCapabilitiesDesc2: branding.homepage_capabilities_desc_2,
        homepageCapabilitiesTitle3: branding.homepage_capabilities_title_3,
        homepageCapabilitiesDesc3: branding.homepage_capabilities_desc_3,
        homepageWorkflow1: branding.homepage_workflow_1,
        homepageWorkflow2: branding.homepage_workflow_2,
        homepageWorkflow3: branding.homepage_workflow_3,
        homepageWorkflow4: branding.homepage_workflow_4,
        homepageWhyTitle: branding.homepage_why_title,
        homepageWhySubtitle: branding.homepage_why_subtitle,
        homepageWhyDescription: branding.homepage_why_description,
        homepageScenariosTitle: branding.homepage_scenarios_title,
        homepageTeamTitle: branding.homepage_team_title,
        homepageTeamSubtitle: branding.homepage_team_subtitle,
        homepageTeamDescription: branding.homepage_team_description,
        homepageTeamButton: branding.homepage_team_button,
      },
    }),
  );
}

type AdminUploadConfig = {
  max_size_mb: number;
  allowed_extensions: string[];
  convert_to_markdown: boolean;
};

type AdminSandboxConfig = {
  use: string;
  allow_host_bash: boolean;
  bash_output_max_chars: number;
  read_file_output_max_chars: number;
  ls_output_max_chars: number;
};

type AdminModelConfig = {
  name: string;
  display_name: string;
  description: string | null;
  use: string;
  model: string;
  api_key: string | null;
  api_base: string | null;
  request_timeout: number;
  max_retries: number;
  max_tokens: number;
  temperature: number;
  supports_vision: boolean;
  supports_thinking: boolean;
  supports_reasoning_effort: boolean;
  is_default: boolean;
  use_responses_api: boolean;
  output_version: string | null;
  thinking: Record<string, unknown> | null;
  when_thinking_enabled: Record<string, unknown> | null;
};

type AdminToolConfig = {
  name: string;
  group: string;
  use: string;
  enabled: boolean;
  extra_params: Record<string, unknown>;
};

type AdminSkillConfig = {
  auto_update: boolean;
  security_scan: boolean;
};

type AdminMCPServerConfig = {
  name: string;
  type: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  url: string | null;
  headers: Record<string, string>;
  description: string;
  enabled: boolean;
};

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
    login_badge: string;
    login_title: string;
    login_subtitle: string;
    feature_title_1: string;
    feature_desc_1: string;
    feature_title_2: string;
    feature_desc_2: string;
    homepage_capabilities_title: string;
    homepage_capabilities_desc: string;
    homepage_capabilities_title_2: string;
    homepage_capabilities_desc_2: string;
    homepage_capabilities_title_3: string;
    homepage_capabilities_desc_3: string;
    homepage_workflow_1: string;
    homepage_workflow_2: string;
    homepage_workflow_3: string;
    homepage_workflow_4: string;
    homepage_why_title: string;
    homepage_why_subtitle: string;
    homepage_why_description: string;
    homepage_scenarios_title: string;
    homepage_team_title: string;
    homepage_team_subtitle: string;
    homepage_team_description: string;
    homepage_team_button: string;
  };
  upload: AdminUploadConfig;
  sandbox: AdminSandboxConfig;
  models: AdminModelConfig[];
  tools: AdminToolConfig[];
  skills: AdminSkillConfig;
  mcp: AdminMCPServerConfig[];
};

export function ConfigAdminPage() {
  const { t } = useI18n();
  const [form, setForm] = useState<AdminConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/admin/config");
        if (!response.ok) throw new Error(t.admin.config.loadFailed);
        setForm((await response.json()) as AdminConfig);
      } catch (err) {
        setError(err instanceof Error ? err.message : t.admin.config.loadFailed);
      }
    }
    void load();
  }, [t.admin.config.loadFailed]);

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
        throw new Error(body?.detail ?? t.admin.config.loadFailed);
      }
      const nextForm = (await response.json()) as AdminConfig;
      setForm(nextForm);
      emitBrandUpdate(nextForm.branding);
      setMessage(t.admin.config.configSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.admin.config.loadFailed);
    } finally {
      setSaving(false);
    }
  }

  if (!form) {
    return (
      <AdminPageShell title={t.admin.config.title} description={t.admin.config.description}>
        <p className="text-sm text-slate-500">{t.admin.config.loading}</p>
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title={t.admin.config.title} description={t.admin.config.description}>
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t.admin.config.systemConfig}</CardTitle>
            <CardDescription>{t.admin.config.tokenUsageDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.config.logLevel}</div>
              <Input value={form.system.log_level ?? ""} onChange={(event) => setForm((current) => current ? { ...current, system: { ...current.system, log_level: event.target.value } } : current)} />
            </div>
            <div className="flex items-center justify-between rounded-2xl border px-4 py-3">
              <div>
                <div className="font-medium">{t.admin.config.enableTokenUsage}</div>
                <div className="text-sm text-slate-500">{t.admin.config.tokenUsageDescription}</div>
              </div>
              <Switch checked={Boolean(form.system.token_usage_enabled)} onCheckedChange={(checked) => setForm((current) => current ? { ...current, system: { ...current.system, token_usage_enabled: checked } } : current)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t.admin.config.brandingConfig}</CardTitle>
            <CardDescription>{t.admin.config.productDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <div className="mb-3 text-sm font-medium text-slate-400 uppercase tracking-wider">{t.admin.config.productName}</div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.productName}</div>
                  <Input value={form.branding.name} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, name: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.shortName}</div>
                  <Input value={form.branding.short_name} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, short_name: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.tagline}</div>
                  <Input value={form.branding.tagline} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, tagline: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.supportEmail}</div>
                  <Input value={form.branding.support_email} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, support_email: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.websitePath}</div>
                  <Input value={form.branding.website_path} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, website_path: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.docsPath}</div>
                  <Input value={form.branding.docs_path} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, docs_path: event.target.value } } : current)} />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <div className="text-sm font-medium">{t.admin.config.productDescription}</div>
                  <Textarea value={form.branding.description} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, description: event.target.value } } : current)} />
                </div>
              </div>
            </div>

            <div className="border-t border-slate-700 pt-6">
              <div className="mb-3 text-sm font-medium text-slate-400 uppercase tracking-wider">{t.admin.config.loginBadge}</div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.loginBadge}</div>
                  <Input value={form.branding.login_badge} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, login_badge: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.loginTitle}</div>
                  <Input value={form.branding.login_title} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, login_title: event.target.value } } : current)} />
                  <div className="text-xs text-slate-500">可用 {"{name}"} {t.admin.config.productName}</div>
                </div>
                <div className="space-y-2 md:col-span-2">
                  <div className="text-sm font-medium">{t.admin.config.loginSubtitle}</div>
                  <Textarea value={form.branding.login_subtitle} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, login_subtitle: event.target.value } } : current)} />
                  <div className="text-xs text-slate-500">可用 {"{name}"} {t.admin.config.productName}</div>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.featureTitle} 1</div>
                  <Input value={form.branding.feature_title_1} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, feature_title_1: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.featureDescription} 1</div>
                  <Input value={form.branding.feature_desc_1} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, feature_desc_1: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.featureTitle} 2</div>
                  <Input value={form.branding.feature_title_2} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, feature_title_2: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.featureDescription} 2</div>
                  <Input value={form.branding.feature_desc_2} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, feature_desc_2: event.target.value } } : current)} />
                </div>
              </div>
            </div>

            <div className="border-t border-slate-700 pt-6">
              <div className="mb-3 text-sm font-medium text-slate-400 uppercase tracking-wider">{t.admin.config.homepageConfig}</div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.capabilityCard} 1</div>
                  <Input value={form.branding.homepage_capabilities_title} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_capabilities_title: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.capabilityCard} 1</div>
                  <Input value={form.branding.homepage_capabilities_desc} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_capabilities_desc: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.capabilityCard} 2</div>
                  <Input value={form.branding.homepage_capabilities_title_2} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_capabilities_title_2: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.capabilityCard} 2</div>
                  <Input value={form.branding.homepage_capabilities_desc_2} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_capabilities_desc_2: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.capabilityCard} 3</div>
                  <Input value={form.branding.homepage_capabilities_title_3} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_capabilities_title_3: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.capabilityCard} 3</div>
                  <Input value={form.branding.homepage_capabilities_desc_3} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_capabilities_desc_3: event.target.value } } : current)} />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <div className="text-sm font-medium">{t.admin.config.workflowsSection}</div>
                  <Textarea
                    value={[form.branding.homepage_workflow_1, form.branding.homepage_workflow_2, form.branding.homepage_workflow_3, form.branding.homepage_workflow_4].join("\n")}
                    onChange={(event) => {
                      const lines = event.target.value.split("\n");
                      setForm((current) => current ? {
                        ...current,
                        branding: {
                          ...current.branding,
                          homepage_workflow_1: lines[0] ?? "",
                          homepage_workflow_2: lines[1] ?? "",
                          homepage_workflow_3: lines[2] ?? "",
                          homepage_workflow_4: lines[3] ?? "",
                        },
                      } : current);
                    }}
                    rows={4}
                  />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <div className="text-sm font-medium">{t.admin.config.whyChooseTitle}</div>
                  <Input value={form.branding.homepage_why_title} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_why_title: event.target.value } } : current)} />
                  <div className="text-xs text-slate-500">可用 {"{name}"} {t.admin.config.productName}</div>
                </div>
                <div className="space-y-2 md:col-span-2">
                  <div className="text-sm font-medium">{t.admin.config.whyChooseSubtitle}</div>
                  <Input value={form.branding.homepage_why_subtitle} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_why_subtitle: event.target.value } } : current)} />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <div className="text-sm font-medium">{t.admin.config.whyChooseDescription}</div>
                  <Textarea value={form.branding.homepage_why_description} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_why_description: event.target.value } } : current)} />
                  <div className="text-xs text-slate-500">可用 {"{name}"} {t.admin.config.productName}</div>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.scenariosTitle}</div>
                  <Input value={form.branding.homepage_scenarios_title} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_scenarios_title: event.target.value } } : current)} />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">{t.admin.config.teamEditionTitle}</div>
                  <Input value={form.branding.homepage_team_title} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_team_title: event.target.value } } : current)} />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <div className="text-sm font-medium">{t.admin.config.teamEditionSubtitle}</div>
                  <Input value={form.branding.homepage_team_subtitle} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_team_subtitle: event.target.value } } : current)} />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <div className="text-sm font-medium">{t.admin.config.teamEditionDescription}</div>
                  <Textarea value={form.branding.homepage_team_description} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_team_description: event.target.value } } : current)} />
                  <div className="text-xs text-slate-500">可用 {"{name}"} 和 {"{support_email}"} {t.admin.config.productName} {t.admin.config.supportEmail}</div>
                </div>
                <div className="space-y-2 md:col-span-2">
                  <div className="text-sm font-medium">{t.admin.config.teamEditionButton}</div>
                  <Input value={form.branding.homepage_team_button} onChange={(event) => setForm((current) => current ? { ...current, branding: { ...current.branding, homepage_team_button: event.target.value } } : current)} />
                  <div className="text-xs text-slate-500">可用 {"{name}"} {t.admin.config.productName}</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.config.tracingConfig}</CardTitle>
          <CardDescription>{t.admin.config.tracingDescription}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-4 rounded-3xl border p-4">
            <div className="flex items-center justify-between">
              <div className="font-medium">{t.admin.config.langsmith}</div>
              <Switch checked={Boolean(form.tracing.langsmith.enabled)} onCheckedChange={(checked) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langsmith: { ...current.tracing.langsmith, enabled: checked } } } : current)} />
            </div>
            <Input value={form.tracing.langsmith.project ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langsmith: { ...current.tracing.langsmith, project: event.target.value } } } : current)} placeholder={t.admin.config.project} />
            <Input value={form.tracing.langsmith.endpoint ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langsmith: { ...current.tracing.langsmith, endpoint: event.target.value } } } : current)} placeholder={t.admin.config.endpoint} />
            <Input value={form.tracing.langsmith.api_key ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langsmith: { ...current.tracing.langsmith, api_key: event.target.value } } } : current)} placeholder="API Key / $ENV_VAR" />
          </div>

          <div className="space-y-4 rounded-3xl border p-4">
            <div className="flex items-center justify-between">
              <div className="font-medium">{t.admin.config.langfuse}</div>
              <Switch checked={Boolean(form.tracing.langfuse.enabled)} onCheckedChange={(checked) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langfuse: { ...current.tracing.langfuse, enabled: checked } } } : current)} />
            </div>
            <Input value={form.tracing.langfuse.host ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langfuse: { ...current.tracing.langfuse, host: event.target.value } } } : current)} placeholder={t.admin.config.host} />
            <Input value={form.tracing.langfuse.public_key ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langfuse: { ...current.tracing.langfuse, public_key: event.target.value } } } : current)} placeholder={`${t.admin.config.publicKey} / $ENV_VAR`} />
            <Input value={form.tracing.langfuse.secret_key ?? ""} onChange={(event) => setForm((current) => current ? { ...current, tracing: { ...current.tracing, langfuse: { ...current.tracing.langfuse, secret_key: event.target.value } } } : current)} placeholder={`${t.admin.config.secretKey} / $ENV_VAR`} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t.admin.config.uploadConfig}</CardTitle>
            <CardDescription>{t.admin.config.autoConvertDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.config.maxFileSize}</div>
              <Input
                type="number"
                value={form.upload.max_size_mb}
                onChange={(event) =>
                  setForm((current) =>
                    current ? { ...current, upload: { ...current.upload, max_size_mb: Number(event.target.value) } } : current,
                  )
                }
              />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.config.allowedExtensions}</div>
              <Input
                value={form.upload.allowed_extensions.join(", ")}
                onChange={(event) =>
                  setForm((current) =>
                    current
                      ? {
                          ...current,
                          upload: {
                            ...current.upload,
                            allowed_extensions: event.target.value.split(",").map((ext) => ext.trim()).filter(Boolean),
                          },
                        }
                      : current,
                  )
                }
              />
            </div>
            <div className="flex items-center justify-between rounded-2xl border px-4 py-3">
              <div>
                <div className="font-medium">{t.admin.config.autoConvertToMarkdown}</div>
                <div className="text-sm text-slate-500">{t.admin.config.autoConvertDescription}</div>
              </div>
              <Switch
                checked={form.upload.convert_to_markdown}
                onCheckedChange={(checked) =>
                  setForm((current) => (current ? { ...current, upload: { ...current.upload, convert_to_markdown: checked } } : current))
                }
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t.admin.config.sandboxConfig}</CardTitle>
            <CardDescription>{t.admin.config.allowHostBashDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="text-sm font-medium">{t.admin.config.sandboxProvider}</div>
              <Input
                value={form.sandbox.use}
                onChange={(event) =>
                  setForm((current) => (current ? { ...current, sandbox: { ...current.sandbox, use: event.target.value } } : current))
                }
              />
            </div>
            <div className="flex items-center justify-between rounded-2xl border px-4 py-3">
              <div>
                <div className="font-medium">{t.admin.config.allowHostBash}</div>
                <div className="text-sm text-slate-500">{t.admin.config.allowHostBashDescription}</div>
              </div>
              <Switch
                checked={form.sandbox.allow_host_bash}
                onCheckedChange={(checked) =>
                  setForm((current) => (current ? { ...current, sandbox: { ...current.sandbox, allow_host_bash: checked } } : current))
                }
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <div className="text-sm font-medium">{t.admin.config.bashOutputMaxChars}</div>
                <Input
                  type="number"
                  value={form.sandbox.bash_output_max_chars}
                  onChange={(event) =>
                    setForm((current) =>
                      current ? { ...current, sandbox: { ...current.sandbox, bash_output_max_chars: Number(event.target.value) } } : current,
                    )
                  }
                />
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium">{t.admin.config.readFileMaxChars}</div>
                <Input
                  type="number"
                  value={form.sandbox.read_file_output_max_chars}
                  onChange={(event) =>
                    setForm((current) =>
                      current
                        ? { ...current, sandbox: { ...current.sandbox, read_file_output_max_chars: Number(event.target.value) } }
                        : current,
                    )
                  }
                />
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium">{t.admin.config.lsOutputMaxChars}</div>
                <Input
                  type="number"
                  value={form.sandbox.ls_output_max_chars}
                  onChange={(event) =>
                    setForm((current) =>
                      current ? { ...current, sandbox: { ...current.sandbox, ls_output_max_chars: Number(event.target.value) } } : current,
                    )
                  }
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.config.skillsConfig}</CardTitle>
          <CardDescription>{t.admin.config.autoUpdateDescription}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center justify-between rounded-2xl border px-4 py-3">
            <div>
              <div className="font-medium">{t.admin.config.autoUpdate}</div>
              <div className="text-sm text-slate-500">{t.admin.config.autoUpdateDescription}</div>
            </div>
            <Switch
              checked={form.skills.auto_update}
              onCheckedChange={(checked) =>
                setForm((current) => (current ? { ...current, skills: { ...current.skills, auto_update: checked } } : current))
              }
            />
          </div>
          <div className="flex items-center justify-between rounded-2xl border px-4 py-3">
            <div>
              <div className="font-medium">{t.admin.config.securityScan}</div>
              <div className="text-sm text-slate-500">{t.admin.config.securityScanDescription}</div>
            </div>
            <Switch
              checked={form.skills.security_scan}
              onCheckedChange={(checked) =>
                setForm((current) => (current ? { ...current, skills: { ...current.skills, security_scan: checked } } : current))
              }
            />
          </div>
        </CardContent>
      </Card>


      <Card>
        <CardHeader>
          <CardTitle>{t.admin.config.toolsConfig}</CardTitle>
          <CardDescription>{t.admin.config.implementationClass}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {form.tools.length === 0 ? (
            <p className="text-sm text-slate-500">{t.admin.config.noMcpServers}</p>
          ) : (
            <div className="space-y-4">
              {form.tools.map((tool, index) => (
                <div key={tool.name || index} className="rounded-2xl border p-4">
                  <div className="mb-4 flex items-center justify-between">
                    <div>
                      <div className="font-medium">{tool.name}</div>
                      <div className="text-sm text-slate-500">{tool.group}</div>
                    </div>
                    <Switch
                      checked={tool.enabled}
                      onCheckedChange={(checked) => {
                        const updated = [...form.tools];
                        const item = updated[index];
                        if (item) {
                          updated[index] = Object.assign({}, item, { enabled: checked });
                          setForm((current) => (current ? { ...current, tools: updated } : current));
                        }
                      }}
                    />
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2 md:col-span-2">
                      <div className="text-sm font-medium">{t.admin.config.implementationClass}</div>
                      <Input
                        value={tool.use || ""}
                        onChange={(event) => {
                          const updated = [...form.tools];
                          const item = updated[index];
                          if (item) {
                            updated[index] = Object.assign({}, item, { use: event.target.value });
                            setForm((current) => (current ? { ...current, tools: updated } : current));
                          }
                        }}
                      />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <div className="text-sm font-medium">{t.admin.config.extraParams}</div>
                      <Textarea
                        value={JSON.stringify(tool.extra_params || {}, null, 2)}
                        onChange={(event) => {
                          const updated = [...form.tools];
                          const item = updated[index];
                          if (item) {
                            try {
                              const extra_params = event.target.value ? JSON.parse(event.target.value) : {};
                              updated[index] = Object.assign({}, item, { extra_params });
                              setForm((current) => (current ? { ...current, tools: updated } : current));
                            } catch {
                              // Invalid JSON, ignore
                            }
                          }
                        }}
                        rows={3}
                        className="font-mono text-xs"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.config.mcpServerConfig}</CardTitle>
          <CardDescription>{t.admin.config.mcpServers}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {form.mcp.length === 0 ? (
            <p className="text-sm text-slate-500">{t.admin.config.noMcpServers}</p>
          ) : (
            form.mcp.map((server, index) => (
              <div key={server.name || index} className="rounded-2xl border p-4">
                <div className="mb-4 flex items-center justify-between">
                  <div className="font-medium">{server.name}</div>
                  <Switch
                    checked={server.enabled}
                    onCheckedChange={(checked) => {
                      const updated = [...form.mcp];
                      const item = updated[index];
                      if (item) {
                        updated[index] = Object.assign({}, item, { enabled: checked });
                        setForm((current) => (current ? { ...current, mcp: updated } : current));
                      }
                    }}
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <div className="text-sm font-medium">{t.admin.config.serverType}</div>
                    <select
                      className="w-full rounded-lg border px-3 py-2"
                      value={server.type || "stdio"}
                      onChange={(event) => {
                        const updated = [...form.mcp];
                        const item = updated[index];
                        if (item) {
                          updated[index] = Object.assign({}, item, { type: event.target.value });
                          setForm((current) => (current ? { ...current, mcp: updated } : current));
                        }
                      }}
                    >
                      <option value="stdio">stdio</option>
                      <option value="sse">sse</option>
                      <option value="http">http</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-medium">{t.admin.config.command}</div>
                    <Input
                      value={server.command || ""}
                      onChange={(event) => {
                        const updated = [...form.mcp];
                        const item = updated[index];
                        if (item) {
                          updated[index] = Object.assign({}, item, { command: event.target.value });
                          setForm((current) => (current ? { ...current, mcp: updated } : current));
                        }
                      }}
                    />
                  </div>
                  {(server.type === "sse" || server.type === "http") && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium">{t.admin.config.url} ({server.type})</div>
                      <Input
                        value={server.url ?? ""}
                        onChange={(event) => {
                          const updated = [...form.mcp];
                          const item = updated[index];
                          if (item) {
                            updated[index] = Object.assign({}, item, { url: event.target.value });
                            setForm((current) => (current ? { ...current, mcp: updated } : current));
                          }
                        }}
                      />
                    </div>
                  )}
                  <div className="space-y-2">
                    <div className="text-sm font-medium">{t.admin.config.args}</div>
                    <Input
                      value={(server.args || []).join(", ")}
                      onChange={(event) => {
                        const updated = [...form.mcp];
                        const item = updated[index];
                        if (item) {
                          updated[index] = Object.assign({}, item, {
                            args: event.target.value.split(",").map((arg) => arg.trim()).filter(Boolean),
                          });
                          setForm((current) => (current ? { ...current, mcp: updated } : current));
                        }
                      }}
                    />
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <div className="text-sm font-medium">{t.admin.config.envVariables}</div>
                    <Input
                      value={Object.entries(server.env || {}).map(([k, v]) => `${k}=${v}`).join(", ")}
                      onChange={(event) => {
                        const updated = [...form.mcp];
                        const item = updated[index];
                        if (item) {
                          const env: Record<string, string> = {};
                          event.target.value.split(",").forEach((pair) => {
                            const [key, ...valueParts] = pair.split("=");
                            if (key?.trim()) {
                              env[key.trim()] = valueParts.join("=").trim();
                            }
                          });
                          updated[index] = Object.assign({}, item, { env });
                          setForm((current) => (current ? { ...current, mcp: updated } : current));
                        }
                      }}
                    />
                  </div>
                  {(server.type === "sse" || server.type === "http") && (
                    <div className="space-y-2 md:col-span-2">
                      <div className="text-sm font-medium">{t.admin.config.headers}</div>
                      <Input
                        value={Object.entries(server.headers || {}).map(([k, v]) => `${k}=${v}`).join(", ")}
                        onChange={(event) => {
                          const updated = [...form.mcp];
                          const item = updated[index];
                          if (item) {
                            const headers: Record<string, string> = {};
                            event.target.value.split(",").forEach((pair) => {
                              const [key, ...valueParts] = pair.split("=");
                              if (key?.trim()) {
                                headers[key.trim()] = valueParts.join("=").trim();
                              }
                            });
                            updated[index] = Object.assign({}, item, { headers });
                            setForm((current) => (current ? { ...current, mcp: updated } : current));
                          }
                        }}
                      />
                    </div>
                  )}
                  <div className="space-y-2 md:col-span-2">
                    <div className="text-sm font-medium">{t.admin.config.description}</div>
                    <Input
                      value={server.description || ""}
                      onChange={(event) => {
                        const updated = [...form.mcp];
                        const item = updated[index];
                        if (item) {
                          updated[index] = Object.assign({}, item, { description: event.target.value });
                          setForm((current) => (current ? { ...current, mcp: updated } : current));
                        }
                      }}
                    />
                  </div>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={() => void save()} disabled={saving}>{saving ? t.admin.config.saving : t.admin.config.saveConfig}</Button>
        {message && <p className="text-sm text-emerald-600">{message}</p>}
        {error && <p className="text-sm text-rose-600">{error}</p>}
      </div>

    </AdminPageShell>
  );
}