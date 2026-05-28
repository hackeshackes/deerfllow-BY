"use client";

import { MicIcon, Volume2Icon } from "lucide-react";
import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { getVoiceConfig, updateVoiceConfig, type VoiceConfig } from "@/lib/api/voice";
import { useI18n } from "@/core/i18n/hooks";

import { AdminPageShell } from "./admin-page-shell";

export function VoiceAdminPage() {
  const { t } = useI18n();
  const [config, setConfig] = useState<VoiceConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadConfig();
  }, []);

  async function loadConfig() {
    try {
      const data = await getVoiceConfig();
      setConfig(data);
    } catch {
      setStatusMessage(t.admin.voice.loadFailed);
    } finally {
      setLoading(false);
    }
  }

  async function saveConfig(updates: Partial<VoiceConfig>) {
    if (!config) return;
    setSaving(true);
    setStatusMessage(null);
    try {
      const updated = await updateVoiceConfig({ ...config, ...updates });
      setConfig(updated);
      setStatusMessage(t.admin.voice.configSaved);
    } catch {
      setStatusMessage(t.admin.voice.configSaveFailed);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <AdminPageShell title={t.admin.voice.title} description={t.admin.voice.description}>
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">{t.admin.voice.loading}</div>
        </div>
      </AdminPageShell>
    );
  }

  if (!config) {
    return (
      <AdminPageShell title={t.admin.voice.title} description={t.admin.voice.description}>
        <div className="flex items-center justify-center py-12">
          <div className="text-destructive">{t.admin.voice.loadFailed}</div>
        </div>
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title={t.admin.voice.title} description={t.admin.voice.description}>
      {statusMessage && (
        <div className="rounded-lg bg-muted px-4 py-2 text-sm">{statusMessage}</div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <MicIcon className="size-5" />
            <CardTitle>STT</CardTitle>
          </div>
          <CardDescription>{t.admin.voice.sttEnabledDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">{t.admin.voice.sttEnabled}</div>
              <div className="text-sm text-muted-foreground">{t.admin.voice.sttEnabledDescription}</div>
            </div>
            <Switch
              checked={config.stt_enabled}
              onCheckedChange={(checked) => saveConfig({ stt_enabled: checked })}
              disabled={saving}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">{t.admin.voice.sttLanguage}</label>
            <Select
              value={config.stt_language}
              onValueChange={(value) => saveConfig({ stt_language: value })}
              disabled={saving}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="zh">{t.admin.voice.chinese}</SelectItem>
                <SelectItem value="en">{t.admin.voice.english}</SelectItem>
                <SelectItem value="auto">{t.admin.voice.autoDetect}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-3">
            <div className="text-sm font-medium">{t.admin.voice.sttModelSize}</div>
            <div className="grid gap-3 md:grid-cols-3">
              <button
                type="button"
                onClick={() => saveConfig({ stt_model_size: "tiny" })}
                disabled={saving}
                className={`rounded-lg border-2 p-4 text-left transition-colors ${
                  config.stt_model_size === "tiny"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <div className="font-medium">{t.admin.voice.modelSizeSmall}</div>
                <div className="mt-1 text-xs text-muted-foreground">{t.admin.voice.modelSizeSmallDesc}</div>
              </button>
              <button
                type="button"
                onClick={() => saveConfig({ stt_model_size: "small" })}
                disabled={saving}
                className={`rounded-lg border-2 p-4 text-left transition-colors ${
                  config.stt_model_size === "small"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <div className="font-medium">{t.admin.voice.modelSizeMedium}</div>
                <div className="mt-1 text-xs text-muted-foreground">{t.admin.voice.modelSizeMediumDesc}</div>
              </button>
              <button
                type="button"
                onClick={() => saveConfig({ stt_model_size: "medium" })}
                disabled={saving}
                className={`rounded-lg border-2 p-4 text-left transition-colors ${
                  config.stt_model_size === "medium"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <div className="font-medium">{t.admin.voice.modelSizeLarge}</div>
                <div className="mt-1 text-xs text-muted-foreground">{t.admin.voice.modelSizeLargeDesc}</div>
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Volume2Icon className="size-5" />
            <CardTitle>TTS</CardTitle>
          </div>
          <CardDescription>{t.admin.voice.ttsEnabledDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">{t.admin.voice.ttsEnabled}</div>
              <div className="text-sm text-muted-foreground">{t.admin.voice.ttsEnabledDescription}</div>
            </div>
            <Switch
              checked={config.tts_enabled}
              onCheckedChange={(checked) => saveConfig({ tts_enabled: checked })}
              disabled={saving}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">{t.admin.voice.voice}</label>
            <Select
              value={config.tts_voice}
              onValueChange={(value) => saveConfig({ tts_voice: value })}
              disabled={saving}
            >
              <SelectTrigger className="w-[250px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="zh-CN-XiaoxiaoNeural">{t.admin.voice.voiceFemale}</SelectItem>
                <SelectItem value="zh-CN-YunxiNeural">{t.admin.voice.voiceMale1}</SelectItem>
                <SelectItem value="zh-CN-YunyangNeural">{t.admin.voice.voiceMale2}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">{t.admin.voice.speed}: {config.tts_speed.toFixed(1)}x</label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={config.tts_speed}
              onChange={(e) => saveConfig({ tts_speed: parseFloat(e.target.value) })}
              disabled={saving}
              className="w-[200px]"
            />
          </div>
        </CardContent>
      </Card>
    </AdminPageShell>
  );
}