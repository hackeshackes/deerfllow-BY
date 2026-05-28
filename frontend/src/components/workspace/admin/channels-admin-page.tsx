"use client";

import { RefreshCwIcon, SettingsIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { AdminPageShell } from "@/components/workspace/admin/admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

type ChannelStatus = {
  service_running: boolean;
  channels: Record<string, { enabled: boolean; running: boolean }>;
};

type ChannelConfig = {
  feishu: { enabled?: boolean; app_id?: string; app_secret?: string } | null;
  slack: { enabled?: boolean; bot_token?: string; app_token?: string } | null;
  telegram: { enabled?: boolean; bot_token?: string } | null;
  wecom: { enabled?: boolean; bot_id?: string; bot_secret?: string } | null;
  dingtalk: { enabled?: boolean; client_id?: string; client_secret?: string } | null;
};

type EditingChannel = {
  id: string;
  name: string;
  enabled: boolean;
  app_id?: string;
  app_secret?: string;
  bot_token?: string;
  app_token?: string;
  bot_id?: string;
  bot_secret?: string;
  corp_id?: string;
  agent_id?: string;
  corp_secret?: string;
  client_id?: string;
  client_secret?: string;
};

const channelInfo = [
  {
    id: "feishu",
    name: "Feishu",
    icon: "📱",
    description: "ByteDance Feishu Platform Integration",
    fields: [
      { key: "app_id", label: "App ID", placeholder: "Feishu App ID" },
      { key: "app_secret", label: "App Secret", placeholder: "Feishu App Secret", isPassword: true },
    ],
  },
  {
    id: "slack",
    name: "Slack",
    icon: "💬",
    description: "Slack Workspace Messaging Integration",
    fields: [
      { key: "bot_token", label: "Bot Token", placeholder: "xoxb-your-bot-token", isPassword: true },
      { key: "app_token", label: "App Token (Socket Mode)", placeholder: "xapp-your-app-token", isPassword: true },
    ],
  },
  {
    id: "telegram",
    name: "Telegram",
    icon: "✈️",
    description: "Telegram Bot Messaging Integration",
    fields: [
      { key: "bot_token", label: "Bot Token", placeholder: "Telegram Bot Token", isPassword: true },
    ],
  },
  {
    id: "wecom",
    name: "WeCom",
    icon: "💼",
    description: "Tencent WeCom Integration",
    fields: [
      { key: "bot_id", label: "Bot ID", placeholder: "WeCom Bot ID" },
      { key: "bot_secret", label: "Bot Secret", placeholder: "WeCom Bot Secret", isPassword: true },
    ],
  },
  {
    id: "dingtalk",
    name: "DingTalk",
    icon: "📌",
    description: "Alibaba DingTalk Platform Integration",
    fields: [
      { key: "client_id", label: "Client ID", placeholder: "DingTalk Client ID" },
      { key: "client_secret", label: "Client Secret", placeholder: "DingTalk Client Secret", isPassword: true },
    ],
  },
];

export function ChannelsAdminPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<ChannelStatus | null>(null);
  const [config, setConfig] = useState<ChannelConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restarting, setRestarting] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingChannel, setEditingChannel] = useState<EditingChannel | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void Promise.all([loadStatus(), loadConfig()]);
  }, []);

  async function loadStatus() {
    try {
      const response = await fetch("/api/channels/");
      if (!response.ok) {
        throw new Error("Failed to load channel status");
      }
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to load status:", err);
    }
  }

  async function loadConfig() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/channels/config");
      if (!response.ok) {
        throw new Error("Failed to load channel config");
      }
      const data = await response.json();
      setConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.admin.channels.title);
    } finally {
      setLoading(false);
    }
  }

  async function handleRestart(channelId: string) {
    setRestarting(channelId);
    try {
      const response = await fetch(`/api/channels/${channelId}/restart`, {
        method: "POST",
      });
      const result = await response.json();
      if (result.success) {
        await loadStatus();
      } else {
        alert(`${t.admin.channels.restartFailed}: ${result.message}`);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : t.admin.channels.restartFailed);
    } finally {
      setRestarting(null);
    }
  }

  async function handleToggle(channelId: string, currentEnabled: boolean) {
    setToggling(channelId);
    try {
      const response = await fetch(`/api/channels/${channelId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !currentEnabled }),
      });
      if (!response.ok) {
        throw new Error(t.admin.channels.updateChannelFailed);
      }
      await Promise.all([loadStatus(), loadConfig()]);
    } catch (err) {
      alert(err instanceof Error ? err.message : t.admin.channels.updateChannelFailed);
    } finally {
      setToggling(null);
    }
  }

  function openEditDialog(channelId: string) {
    const channel = channelInfo.find((c) => c.id === channelId);
    if (!channel) return;

    const channelConfig = (config?.[channelId as keyof ChannelConfig] ?? {}) as Record<string, string | boolean | undefined>;
    setEditingChannel({
      id: channelId,
      name: channel.name,
      enabled: (channelConfig.enabled as boolean | undefined) ?? false,
      app_id: (channelConfig.app_id as string | undefined) ?? "",
      app_secret: (channelConfig.app_secret as string | undefined) ?? "",
      bot_token: (channelConfig.bot_token as string | undefined) ?? "",
      app_token: (channelConfig.app_token as string | undefined) ?? "",
      bot_id: (channelConfig.bot_id as string | undefined) ?? "",
      bot_secret: (channelConfig.bot_secret as string | undefined) ?? "",
      corp_id: (channelConfig.corp_id as string | undefined) ?? "",
      agent_id: (channelConfig.agent_id as string | undefined) ?? "",
      corp_secret: (channelConfig.corp_secret as string | undefined) ?? "",
      client_id: (channelConfig.client_id as string | undefined) ?? "",
      client_secret: (channelConfig.client_secret as string | undefined) ?? "",
    });
    setEditDialogOpen(true);
  }

  async function handleSave() {
    if (!editingChannel) return;
    setSaving(true);
    try {
      const payload: Record<string, string | boolean> = {
        enabled: editingChannel.enabled,
      };
      if (editingChannel.app_id) payload.app_id = editingChannel.app_id;
      if (editingChannel.app_secret) payload.app_secret = editingChannel.app_secret;
      if (editingChannel.bot_token) payload.bot_token = editingChannel.bot_token;
      if (editingChannel.app_token) payload.app_token = editingChannel.app_token;
      if (editingChannel.bot_id) payload.bot_id = editingChannel.bot_id;
      if (editingChannel.bot_secret) payload.bot_secret = editingChannel.bot_secret;
      if (editingChannel.client_id) payload.client_id = editingChannel.client_id;
      if (editingChannel.client_secret) payload.client_secret = editingChannel.client_secret;

      const response = await fetch(`/api/channels/${editingChannel.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(t.admin.channels.saveConfigFailed);
      }
      setEditDialogOpen(false);
      await Promise.all([loadStatus(), loadConfig()]);
    } catch (err) {
      alert(err instanceof Error ? err.message : t.admin.channels.saveConfigFailed);
    } finally {
      setSaving(false);
    }
  }

  const currentChannel = channelInfo.find((c) => c.id === editingChannel?.id);

  return (
    <AdminPageShell
      title={t.admin.channels.title}
      description={t.admin.channels.description}
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium">{t.admin.channels.channelStatus}</h3>
            <p className="text-sm text-muted-foreground">
              {t.admin.channels.serviceRunning}: {status?.service_running ? "✅" : "❌"}
            </p>
          </div>
          <Button variant="outline" onClick={() => Promise.all([loadStatus(), loadConfig()])} disabled={loading}>
            <RefreshCwIcon className={`size-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            {t.admin.channels.refreshStatus}
          </Button>
        </div>

        {loading && !status && !config ? (
          <div className="text-center py-8 text-muted-foreground">{t.admin.voice.loading}</div>
        ) : error ? (
          <Card>
            <CardContent className="py-8 text-center text-red-500">{error}</CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {channelInfo.map((channel) => {
              const channelStatus = status?.channels?.[channel.id];
              const channelConfig = (config?.[channel.id as keyof ChannelConfig] ?? {}) as Record<string, string | boolean | undefined>;
              const isEnabled = channelStatus?.enabled ?? (channelConfig.enabled as boolean | undefined);
              const isRunning = channelStatus?.running;
              const hasConfig = Object.keys(channelConfig).some(
                (k) => k !== "enabled" && channelConfig[k]
              );

              return (
                <Card key={channel.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{channel.icon}</span>
                        <div>
                          <CardTitle className="text-lg">{channel.name}</CardTitle>
                          <CardDescription>{channel.description}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-1 text-xs ${
                            isRunning
                              ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
                              : isEnabled
                                ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100"
                                : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
                          }`}
                        >
                          {isRunning ? t.admin.channels.running : isEnabled ? t.admin.channels.enabled : t.admin.channels.notConfigured}
                        </span>
                        <Switch
                          checked={!!isEnabled}
                          onCheckedChange={() => handleToggle(channel.id, !!isEnabled)}
                          disabled={toggling === channel.id || isRunning}
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openEditDialog(channel.id)}
                        >
                          <SettingsIcon className="size-4" />
                          {t.admin.channels.configure}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRestart(channel.id)}
                          disabled={restarting === channel.id || !isEnabled}
                        >
                          <RefreshCwIcon
                            className={`size-4 mr-1 ${restarting === channel.id ? "animate-spin" : ""}`}
                          />
                          {t.admin.channels.restart}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {hasConfig ? (
                      <div className="text-sm text-muted-foreground space-y-1">
                        {typeof channelConfig.app_id === "string" && channelConfig.app_id && (
                          <div>App ID: {channelConfig.app_id.slice(0, 8)}***</div>
                        )}
                        {typeof channelConfig.bot_token === "string" && channelConfig.bot_token && (
                          <div>Bot Token: {channelConfig.bot_token.slice(0, 8)}***</div>
                        )}
                        {typeof channelConfig.app_token === "string" && channelConfig.app_token && (
                          <div>App Token: {channelConfig.app_token.slice(0, 8)}***</div>
                        )}
                        {typeof channelConfig.bot_id === "string" && channelConfig.bot_id && (
                          <div>Bot ID: {channelConfig.bot_id}</div>
                        )}
                        {typeof channelConfig.client_id === "string" && channelConfig.client_id && (
                          <div>Client ID: {channelConfig.client_id.slice(0, 8)}***</div>
                        )}
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground">
                        {t.admin.channels.noConfig}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingChannel?.name} {t.admin.channels.configure}</DialogTitle>
            <DialogDescription>{t.admin.channels.channelDescription}</DialogDescription>
          </DialogHeader>
          {editingChannel && currentChannel && (
            <div className="space-y-4 py-4">
              <div className="flex items-center justify-between rounded-lg border px-3 py-2">
                <span className="text-sm font-medium">{t.admin.channels.enableChannel}</span>
                <Switch
                  checked={editingChannel.enabled}
                  onCheckedChange={(checked) =>
                    setEditingChannel({ ...editingChannel, enabled: checked })
                  }
                />
              </div>
              {currentChannel.fields.map((field) => (
                <div key={field.key} className="space-y-2">
                  <label className="text-sm font-medium">{field.label}</label>
                  <Input
                    type={field.isPassword ? "password" : "text"}
                    value={
                      editingChannel[field.key as keyof EditingChannel] as string || ""
                    }
                    onChange={(e) =>
                      setEditingChannel({
                        ...editingChannel,
                        [field.key]: e.target.value,
                      })
                    }
                    placeholder={field.placeholder}
                  />
                </div>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              {t.admin.channels.cancel}
            </Button>
            <Button onClick={() => void handleSave()} disabled={saving}>
              {saving ? t.admin.channels.saving : t.admin.channels.saveConfig}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}