"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useI18n } from "@/core/i18n/hooks";

import { AdminPageShell } from "./admin-page-shell";

type SecretState = "missing" | "placeholder" | "fresh" | "configured";

type SecretStatusItem = {
  key: string;
  state: SecretState;
  is_placeholder: boolean;
  last_rotated_at: string | null;
  source: "vault" | "env" | "seed_default";
  masked_value: string | null;
};

type SecretStatusResponse = {
  items: SecretStatusItem[];
  known_keys: string[];
  vault_mtime: string | null;
};

type AdminAuditEvent = {
  ts: string;
  action: string;
  actor_id: string | null;
  target: string;
  details: Record<string, string | number | boolean | null>;
};

type AdminAuditResponse = {
  events: AdminAuditEvent[];
  action_prefix: string | null;
  actor_id: string | null;
};

const STATE_BADGE: Record<SecretState, "default" | "secondary" | "destructive" | "outline"> = {
  missing: "outline",
  placeholder: "destructive",
  fresh: "default",
  configured: "secondary",
};

export function SecretsAdminPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<SecretStatusResponse | null>(null);
  const [audit, setAudit] = useState<AdminAuditResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [upsertKey, setUpsertKey] = useState("");
  const [upsertValue, setUpsertValue] = useState("");
  const [rotateKey, setRotateKey] = useState("");
  const [rotateValue, setRotateValue] = useState("");
  const [rotatePassword, setRotatePassword] = useState("");
  const [submitting, setSubmitting] = useState<null | "upsert" | "rotate">(null);

  const refresh = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([
        fetch("/api/admin/secrets/status?include_all=true", { credentials: "include" }),
        fetch("/api/admin/secrets/audit-events?action_prefix=admin_secret.", { credentials: "include" }),
      ]);
      if (!s.ok) throw new Error("status fetch failed");
      if (!a.ok) throw new Error("audit fetch failed");
      setStatus((await s.json()) as SecretStatusResponse);
      setAudit((await a.json()) as AdminAuditResponse);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleUpsert = useCallback(async () => {
    if (!upsertKey || !upsertValue) return;
    setSubmitting("upsert");
    try {
      const r = await fetch("/api/admin/secrets/upsert", {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ key: upsertKey, value: upsertValue }),
      });
      if (!r.ok) {
        const detail = (await r.json().catch(() => ({}))) as { detail?: string };
        throw new Error(detail.detail ?? `upsert failed (${r.status})`);
      }
      setUpsertValue("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "upsert failed");
    } finally {
      setSubmitting(null);
    }
  }, [upsertKey, upsertValue, refresh]);

  const handleRotate = useCallback(async () => {
    if (!rotateKey || !rotateValue || !rotatePassword) return;
    setSubmitting("rotate");
    try {
      const r = await fetch("/api/admin/secrets/rotate", {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          key: rotateKey,
          new_value: rotateValue,
          current_admin_password: rotatePassword,
        }),
      });
      if (!r.ok) {
        const detail = (await r.json().catch(() => ({}))) as { detail?: string };
        throw new Error(detail.detail ?? `rotate failed (${r.status})`);
      }
      setRotateValue("");
      setRotatePassword("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "rotate failed");
    } finally {
      setSubmitting(null);
    }
  }, [rotateKey, rotateValue, rotatePassword, refresh]);

  return (
    <AdminPageShell title={t.admin.secrets.title} description={t.admin.secrets.description}>
      <Tabs defaultValue="status">
        <TabsList>
          <TabsTrigger value="status">{t.admin.secrets.tabStatus}</TabsTrigger>
          <TabsTrigger value="upsert">{t.admin.secrets.tabUpsert}</TabsTrigger>
          <TabsTrigger value="rotate">{t.admin.secrets.tabRotate}</TabsTrigger>
          <TabsTrigger value="audit">{t.admin.secrets.tabAudit}</TabsTrigger>
        </TabsList>

        <TabsContent value="status">
          <Card>
            <CardHeader>
              <CardTitle>{t.admin.secrets.statusTitle}</CardTitle>
              <CardDescription>{t.admin.secrets.statusDescription}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {error ? <div className="text-destructive text-sm">{error}</div> : null}
              {!status ? (
                <div className="text-muted-foreground text-sm">{t.admin.secrets.loading}</div>
              ) : (
                <div className="divide-y">
                  {status.items.map((item) => (
                    <div key={item.key} className="flex items-center justify-between py-2 text-sm">
                      <div className="font-mono">{item.key}</div>
                      <div className="flex items-center gap-3">
                        <Badge variant={STATE_BADGE[item.state]}>{item.state}</Badge>
                        <span className="text-muted-foreground">{item.source}</span>
                        <span className="w-32 text-right font-mono text-xs">{item.masked_value ?? "—"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="upsert">
          <Card>
            <CardHeader>
              <CardTitle>{t.admin.secrets.upsertTitle}</CardTitle>
              <CardDescription>{t.admin.secrets.upsertDescription}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input placeholder={t.admin.secrets.keyPlaceholder} value={upsertKey} onChange={(e) => setUpsertKey(e.target.value)} />
              <Input
                type="password"
                placeholder={t.admin.secrets.valuePlaceholder}
                value={upsertValue}
                onChange={(e) => setUpsertValue(e.target.value)}
              />
              <Button disabled={submitting !== null || !upsertKey || !upsertValue} onClick={handleUpsert}>
                {submitting === "upsert" ? t.admin.secrets.submitting : t.admin.secrets.upsert}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rotate">
          <Card>
            <CardHeader>
              <CardTitle>{t.admin.secrets.rotateTitle}</CardTitle>
              <CardDescription>{t.admin.secrets.rotateDescription}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input placeholder={t.admin.secrets.keyPlaceholder} value={rotateKey} onChange={(e) => setRotateKey(e.target.value)} />
              <Input
                type="password"
                placeholder={t.admin.secrets.valuePlaceholder}
                value={rotateValue}
                onChange={(e) => setRotateValue(e.target.value)}
              />
              <Input
                type="password"
                placeholder={t.admin.secrets.passwordPlaceholder}
                value={rotatePassword}
                onChange={(e) => setRotatePassword(e.target.value)}
              />
              <Button
                disabled={submitting !== null || !rotateKey || !rotateValue || !rotatePassword}
                onClick={handleRotate}
              >
                {submitting === "rotate" ? t.admin.secrets.submitting : t.admin.secrets.rotate}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit">
          <Card>
            <CardHeader>
              <CardTitle>{t.admin.secrets.auditTitle}</CardTitle>
              <CardDescription>{t.admin.secrets.auditDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              {!audit ? (
                <div className="text-muted-foreground text-sm">{t.admin.secrets.loading}</div>
              ) : audit.events.length === 0 ? (
                <div className="text-muted-foreground text-sm">{t.admin.secrets.auditEmpty}</div>
              ) : (
                <div className="divide-y text-sm">
                  {audit.events.map((e, i) => (
                    <div key={`${e.ts}-${i}`} className="flex items-center justify-between py-2">
                      <div>
                        <div className="font-mono">{e.action}</div>
                        <div className="text-muted-foreground text-xs">{e.target}</div>
                      </div>
                      <div className="text-muted-foreground text-xs">{e.ts}</div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </AdminPageShell>
  );
}