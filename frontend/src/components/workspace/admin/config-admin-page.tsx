"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

import { AdminPageShell } from "./admin-page-shell";

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
  };
  upload: AdminUploadConfig;
  sandbox: AdminSandboxConfig;
  models: AdminModelConfig[];
  tools: AdminToolConfig[];
  skills: AdminSkillConfig;
  mcp: AdminMCPServerConfig[];
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
      const nextForm = (await response.json()) as AdminConfig;
      setForm(nextForm);
      emitBrandUpdate(nextForm.branding);
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

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>上传配置</CardTitle>
            <CardDescription>控制文件上传的大小限制和格式。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="text-sm font-medium">最大文件大小 (MB)</div>
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
              <div className="text-sm font-medium">允许的文件扩展名 (逗号分隔)</div>
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
                <div className="font-medium">自动转换为 Markdown</div>
                <div className="text-sm text-slate-500">将 PDF、PPT、Word、Excel 文件自动转为 Markdown。</div>
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
            <CardTitle>沙箱配置</CardTitle>
            <CardDescription>控制代码执行沙箱的行为。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="text-sm font-medium">沙箱 Provider</div>
              <Input
                value={form.sandbox.use}
                onChange={(event) =>
                  setForm((current) => (current ? { ...current, sandbox: { ...current.sandbox, use: event.target.value } } : current))
                }
              />
            </div>
            <div className="flex items-center justify-between rounded-2xl border px-4 py-3">
              <div>
                <div className="font-medium">允许宿主 Bash</div>
                <div className="text-sm text-slate-500">允许在宿主系统执行 Bash 命令。</div>
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
                <div className="text-sm font-medium">Bash 输出最大字符</div>
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
                <div className="text-sm font-medium">读取文件最大字符</div>
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
                <div className="text-sm font-medium">ls 输出最大字符</div>
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
          <CardTitle>技能配置</CardTitle>
          <CardDescription>控制技能的安全扫描和自动更新。</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center justify-between rounded-2xl border px-4 py-3">
            <div>
              <div className="font-medium">自动更新</div>
              <div className="text-sm text-slate-500">自动更新已安装的技能到最新版本。</div>
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
              <div className="font-medium">安全扫描</div>
              <div className="text-sm text-slate-500">安装前扫描技能文件的安全性。</div>
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
          <CardTitle>工具配置</CardTitle>
          <CardDescription>配置可用的工具及其启用状态。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {form.tools.length === 0 ? (
            <p className="text-sm text-slate-500">暂无工具配置。</p>
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
                      <div className="text-sm font-medium">实现类路径</div>
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
                      <div className="text-sm font-medium">额外参数 (JSON 格式)</div>
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
          <CardTitle>MCP 服务器配置</CardTitle>
          <CardDescription>配置 Model Context Protocol 服务器。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {form.mcp.length === 0 ? (
            <p className="text-sm text-slate-500">暂无 MCP 服务器配置。</p>
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
                    <div className="text-sm font-medium">类型</div>
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
                    <div className="text-sm font-medium">命令 (仅 stdio)</div>
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
                      <div className="text-sm font-medium">URL ({server.type})</div>
                      <Input
                        value={server.url || ""}
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
                    <div className="text-sm font-medium">参数 (逗号分隔)</div>
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
                    <div className="text-sm font-medium">环境变量 (key=value, 逗号分隔)</div>
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
                      <div className="text-sm font-medium">请求头 (key=value, 逗号分隔)</div>
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
                    <div className="text-sm font-medium">描述</div>
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
        <Button onClick={() => void save()} disabled={saving}>{saving ? "保存中..." : "保存配置"}</Button>
        {message && <p className="text-sm text-emerald-600">{message}</p>}
        {error && <p className="text-sm text-rose-600">{error}</p>}
      </div>

    </AdminPageShell>
  );
}
