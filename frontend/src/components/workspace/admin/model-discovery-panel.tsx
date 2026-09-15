"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type DiscoveredItem = {
  id: string;
  display_name: string;
  supports_vision: boolean;
  supports_thinking: boolean;
};

type DiscoveryResp = {
  provider: string;
  base_url: string | null;
  discovered: boolean;
  models: DiscoveredItem[];
  error_message: string | null;
  fallback_presets: boolean;
};

const PROVIDERS = [
  { value: "openai", label: "OpenAI 兼容 / OpenAI" },
  { value: "anthropic", label: "Anthropic Claude" },
  { value: "gemini", label: "Google Gemini" },
];

type Props = {
  onPick: (context: {
    provider: string;
    base_url: string;
    api_key: string;
    model: DiscoveredItem;
  }) => void;
};

export function ModelDiscoveryPanel({ onPick }: Props) {
  const [provider, setProvider] = useState("openai");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<DiscoveryResp | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function discover() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch("/api/admin/models/inspect", {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ provider, base_url: baseUrl || undefined, api_key: apiKey || undefined }),
      });
      if (!r.ok) {
        const d = (await r.json().catch(() => ({}))) as { detail?: string };
        throw new Error(d.detail ?? `discover failed (${r.status})`);
      }
      setResult((await r.json()) as DiscoveryResp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "discover failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>模型自动发现</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="space-y-1">
            <div className="text-sm font-medium">协议</div>
            <Select value={provider} onValueChange={setProvider}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <div className="text-sm font-medium">API 地址（base_url）</div>
            <Input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          <div className="space-y-1">
            <div className="text-sm font-medium">API Key</div>
            <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-…" />
          </div>
        </div>

        <Button onClick={discover} disabled={busy}>
          {busy ? "发现中…" : "读取可用模型"}
        </Button>

        {error && <p className="text-sm text-rose-600">{error}</p>}
        {result && !result.discovered && (
          <p className="text-sm text-amber-600">
            {result.error_message ? `发现失败：${result.error_message}` : "未发现可用模型"}（已回退到预置清单）
          </p>
        )}
        {result && result.discovered && result.models.length === 0 && (
          <p className="text-sm text-slate-500">该网关没有返回可用模型。</p>
        )}

        {result?.models.length ? (
          <div className="grid gap-2 md:grid-cols-2">
            {result.models.map((m) => (
              <div key={m.id} className="flex items-center justify-between rounded-xl border px-3 py-2">
                <div className="min-w-0">
                  <div className="truncate font-medium">{m.display_name || m.id}</div>
                  <div className="text-muted-foreground text-xs truncate">{m.id}</div>
                  <div className="text-muted-foreground text-xs">
                    {[m.supports_vision && "视觉", m.supports_thinking && "思考"].filter(Boolean).join(" · ") || "—"}
                  </div>
                </div>
                <Button size="sm" variant="outline" onClick={() => onPick({ provider, base_url: baseUrl, api_key: apiKey, model: m })}>
                  以此新增
                </Button>
              </div>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}