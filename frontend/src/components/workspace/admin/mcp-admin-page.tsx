"use client";

import { CopyIcon, PlusIcon, TrashIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { AdminPageShell } from "@/components/workspace/admin/admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";
import type { MCPServerConfig, MCPPreset } from "@/core/mcp/types";

const defaultServerConfig: MCPServerConfig = {
  enabled: true,
  type: "stdio",
  command: "",
  args: [],
  env: {},
  url: "",
  headers: {},
  oauth: null,
  description: "",
};

export function MCPAdminPage() {
  const { t } = useI18n();
  const [servers, setServers] = useState<Record<string, MCPServerConfig>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [presetDialogOpen, setPresetDialogOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<string | null>(null);
  const [form, setForm] = useState<MCPServerConfig>(defaultServerConfig);
  const [serverName, setServerName] = useState("");
  const [testResult, setTestResult] = useState<{ success: boolean; error?: string } | null>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [presets, setPresets] = useState<MCPPreset[]>([]);

  useEffect(() => {
    void loadServers();
    void loadPresets();
  }, []);

  async function loadServers() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/mcp/config");
      if (!response.ok) {
        throw new Error(t.admin.mcp.loadFailed);
      }
      const data = await response.json();
      setServers(data.mcp_servers ?? {});
    } catch (err) {
      setError(err instanceof Error ? err.message : t.admin.mcp.loadFailed);
    } finally {
      setLoading(false);
    }
  }

  async function loadPresets() {
    try {
      const response = await fetch("/api/mcp/presets");
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      setPresets(data.presets ?? []);
    } catch {
      // ignore preset loading errors
    }
  }

  async function saveServers(updatedServers: Record<string, MCPServerConfig>) {
    setSaving(true);
    try {
      const response = await fetch("/api/mcp/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mcp_servers: updatedServers }),
      });
      if (!response.ok) {
        throw new Error(t.admin.mcp.loadFailed);
      }
      const data = await response.json();
      setServers(data.mcp_servers ?? {});
      setDialogOpen(false);
      setEditingServer(null);
      setForm(defaultServerConfig);
      setServerName("");
    } catch (err) {
      alert(err instanceof Error ? err.message : t.admin.mcp.loadFailed);
    } finally {
      setSaving(false);
    }
  }

  function openCreateDialog() {
    setEditingServer(null);
    setServerName("");
    setForm({ ...defaultServerConfig });
    setTestResult(null);
    setDialogOpen(true);
  }

  function openEditDialog(name: string) {
    const server = servers[name];
    if (!server) return;
    setEditingServer(name);
    setServerName(name);
    setForm({ ...server });
    setTestResult(null);
    setDialogOpen(true);
  }

  function openPresetDialog() {
    setPresetDialogOpen(true);
  }

  function selectPreset(preset: MCPPreset) {
    const newName = preset.id;
    setEditingServer(null);
    setServerName(newName);
    setForm({ ...defaultServerConfig, ...preset.server });
    setTestResult(null);
    setPresetDialogOpen(false);
    setDialogOpen(true);
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const response = await fetch("/api/mcp/servers/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const result = await response.json();
      setTestResult(result);
    } catch {
      setTestResult({ success: false, error: t.admin.mcp.connectionFailed });
    } finally {
      setTesting(false);
    }
  }

  function handleSave() {
    if (!serverName.trim()) {
      alert(t.admin.mcp.serverName);
      return;
    }
    const updatedServers = { ...servers };
    if (editingServer && editingServer !== serverName) {
      delete updatedServers[editingServer];
    }
    updatedServers[serverName] = form;
    void saveServers(updatedServers);
  }

  function handleDelete(name: string) {
    if (!confirm(t.admin.mcp.deleteConfirm.replace("{name}", name))) return;
    const updatedServers = { ...servers };
    delete updatedServers[name];
    void saveServers(updatedServers);
  }

  function handleToggle(name: string) {
    const updatedServers = { ...servers };
    const current = updatedServers[name];
    if (current) {
      updatedServers[name] = { ...current, enabled: !current.enabled } as MCPServerConfig;
      void saveServers(updatedServers);
    }
  }

  function copyEnvTemplate() {
    const envLines = Object.entries(form.env)
      .map(([key]) => `${key}=`)
      .join("\n");
    void navigator.clipboard.writeText(envLines);
  }

  return (
    <AdminPageShell
      title={t.admin.mcp.title}
      description={t.admin.mcp.description}
    >
      <div className="space-y-6">
        {loading ? (
          <div className="text-center py-8 text-muted-foreground">{t.admin.mcp.loading}</div>
        ) : error ? (
          <div className="text-center py-8 text-red-500">{error}</div>
        ) : (
          <>
            <div className="flex gap-2">
              <Button onClick={openCreateDialog}>
                <PlusIcon className="size-4 mr-1" />
                {t.admin.mcp.addCustomServer}
              </Button>
              <Button variant="outline" onClick={openPresetDialog}>
                {t.admin.mcp.addFromPreset}
              </Button>
            </div>

            {Object.keys(servers).length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center text-muted-foreground">
                  {t.admin.mcp.noMcpServers}
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {Object.entries(servers).map(([name, config]) => (
                  <Card key={name}>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CardTitle className="text-lg">{name}</CardTitle>
                          <Switch checked={config.enabled} onCheckedChange={() => handleToggle(name)} />
                        </div>
                        <div className="flex gap-1">
                          <Button size="sm" variant="outline" onClick={() => openEditDialog(name)}>
                            {t.admin.mcp.edit}
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => handleDelete(name)}>
                            <TrashIcon className="size-4" />
                          </Button>
                        </div>
                      </div>
                      <CardDescription>{config.description || t.admin.mcp.noDescription}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="text-sm text-muted-foreground">
                        <div>{t.admin.mcp.serverType}: {config.type}</div>
                        {config.command && <div>{t.admin.mcp.command}: {config.command} {config.args?.join(" ")}</div>}
                        {config.url && <div>{t.admin.mcp.url}: {config.url}</div>}
                        {Object.keys(config.env || {}).length > 0 && (
                          <div>{t.admin.mcp.envVariables}: {Object.keys(config.env).join(", ")}</div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingServer ? t.admin.mcp.editServer : t.admin.mcp.createServer}</DialogTitle>
            <DialogDescription>
              {editingServer ? `${editingServer}` : t.admin.mcp.serverDescription}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">{t.admin.mcp.serverName}</label>
                <Input
                  value={serverName}
                  onChange={(e) => setServerName(e.target.value)}
                  placeholder="my-mcp-server"
                  disabled={!!editingServer}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">{t.admin.mcp.serverType}</label>
                <select
                  className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value as "stdio" | "sse" | "http" })}
                >
                  <option value="stdio">STDIO</option>
                  <option value="sse">SSE</option>
                  <option value="http">HTTP</option>
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">{t.admin.mcp.serverDescription}</label>
              <Input
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder={t.admin.mcp.serverDescription}
              />
            </div>

            {form.type === "stdio" ? (
              <>
                <div className="space-y-2">
                  <label className="text-sm font-medium">{t.admin.mcp.command}</label>
                  <Input
                    value={form.command ?? ""}
                    onChange={(e) => setForm({ ...form, command: e.target.value })}
                    placeholder="npx"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">{t.admin.mcp.args}</label>
                  <Input
                    value={form.args?.join(" ") ?? ""}
                    onChange={(e) => setForm({ ...form, args: e.target.value.split(" ").filter(Boolean) })}
                    placeholder="-y @modelcontextprotocol/server-github"
                  />
                </div>
              </>
            ) : (
              <div className="space-y-2">
                <label className="text-sm font-medium">{t.admin.mcp.url}</label>
                <Input
                  value={form.url ?? ""}
                  onChange={(e) => setForm({ ...form, url: e.target.value })}
                  placeholder="https://api.example.com/mcp"
                />
              </div>
            )}

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">{t.admin.mcp.envVariables}</label>
                <Button size="sm" variant="ghost" onClick={copyEnvTemplate}>
                  <CopyIcon className="size-4 mr-1" />
                  {t.admin.mcp.copyTemplate}
                </Button>
              </div>
              <Textarea
                value={Object.entries(form.env || {})
                  .map(([k, v]) => `${k}=${v}`)
                  .join("\n")}
                onChange={(e) => {
                  const env: Record<string, string> = {};
                  e.target.value.split("\n").forEach((line) => {
                    const [key, ...vals] = line.split("=");
                    if (key) env[key.trim()] = vals.join("=");
                  });
                  setForm({ ...form, env });
                }}
                placeholder="KEY=value"
                rows={4}
              />
            </div>

            {testResult && (
              <div className={`p-3 rounded-md ${testResult.success ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
                {testResult.success ? t.admin.mcp.connectionSuccess : `${t.admin.mcp.connectionFailed}: ${testResult.error}`}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleTest} disabled={testing}>
              {testing ? t.admin.mcp.testing : t.admin.mcp.testConnection}
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? t.admin.mcp.saving : t.admin.mcp.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={presetDialogOpen} onOpenChange={setPresetDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.admin.mcp.selectPreset}</DialogTitle>
            <DialogDescription>{t.admin.mcp.serverDescription}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            {presets.map((preset) => (
              <div
                key={preset.id}
                className="flex items-center justify-between p-4 rounded-lg border cursor-pointer hover:bg-muted/50"
                onClick={() => selectPreset(preset)}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{preset.icon}</span>
                    <span className="font-medium">{preset.name}</span>
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">{preset.description}</div>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}