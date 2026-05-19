"use client";

import { MicIcon, Settings2Icon, Volume2Icon } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
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

import { AdminPageShell } from "./admin-page-shell";

const STT_MODEL_OPTIONS = [
  { value: "tiny", label: "小（tiny）", description: "快速响应，低资源占用" },
  { value: "small", label: "中（small）", description: "平衡模式（推荐）" },
  { value: "medium", label: "大（medium）", description: "高质量，需较强算力" },
];

const STT_LANGUAGE_OPTIONS = [
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
  { value: "auto", label: "自动检测" },
];

export function VoiceAdminPage() {
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
      setStatusMessage("加载语音配置失败");
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
      setStatusMessage("配置已保存");
    } catch {
      setStatusMessage("保存配置失败");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <AdminPageShell title="语音配置" description="配置语音转文字和语音合成功能">
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">加载中...</div>
        </div>
      </AdminPageShell>
    );
  }

  if (!config) {
    return (
      <AdminPageShell title="语音配置" description="配置语音转文字和语音合成功能">
        <div className="flex items-center justify-center py-12">
          <div className="text-destructive">加载配置失败</div>
        </div>
      </AdminPageShell>
    );
  }

  return (
    <AdminPageShell title="语音配置" description="配置语音转文字（STT）和语音合成（TTS）功能">
      {statusMessage && (
        <div className="rounded-lg bg-muted px-4 py-2 text-sm">{statusMessage}</div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <MicIcon className="size-5" />
            <CardTitle>语音转文字（STT）</CardTitle>
          </div>
          <CardDescription>配置语音识别功能，将麦克风输入转为文字</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">启用 STT</div>
              <div className="text-sm text-muted-foreground">开启后用户可使用麦克风输入</div>
            </div>
            <Switch
              checked={config.stt_enabled}
              onCheckedChange={(checked) => saveConfig({ stt_enabled: checked })}
              disabled={saving}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">识别语言</label>
            <Select
              value={config.stt_language}
              onValueChange={(value) => saveConfig({ stt_language: value })}
              disabled={saving}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STT_LANGUAGE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-3">
            <div className="text-sm font-medium">模型大小</div>
            <div className="grid gap-3 md:grid-cols-3">
              {STT_MODEL_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => saveConfig({ stt_model_size: opt.value as VoiceConfig["stt_model_size"] })}
                  disabled={saving}
                  className={`rounded-lg border-2 p-4 text-left transition-colors ${
                    config.stt_model_size === opt.value
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <div className="font-medium">{opt.label}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{opt.description}</div>
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Volume2Icon className="size-5" />
            <CardTitle>语音合成（TTS）</CardTitle>
          </div>
          <CardDescription>配置语音播报功能，开启后可在AI回复时选择语音播报</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">启用 TTS</div>
              <div className="text-sm text-muted-foreground">开启后 AI 回答可选择语音播报</div>
            </div>
            <Switch
              checked={config.tts_enabled}
              onCheckedChange={(checked) => saveConfig({ tts_enabled: checked })}
              disabled={saving}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">音色</label>
            <Select
              value={config.tts_voice}
              onValueChange={(value) => saveConfig({ tts_voice: value })}
              disabled={saving}
            >
              <SelectTrigger className="w-[250px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="zh-CN-XiaoxiaoNeural">晓晓（女声）</SelectItem>
                <SelectItem value="zh-CN-YunxiNeural">云希（男声）</SelectItem>
                <SelectItem value="zh-CN-YunyangNeural">云扬（男声）</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">语速: {config.tts_speed.toFixed(1)}x</label>
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