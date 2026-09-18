"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useI18n } from "@/core/i18n/hooks";

import { AdminPageShell } from "./admin-page-shell";

type Policy = {
  id: string;
  effect: "allow" | "deny";
  combiner?: string;
  applies_to?: string[];
  conditions?: { op: string; path: string; value: unknown }[];
  [key: string]: unknown;
};

type PoliciesPayload = {
  version: number;
  policies: Policy[];
};

const EFFECT_STYLE: Record<string, "default" | "destructive" | "outline"> = {
  allow: "default",
  deny: "destructive",
};

export function AbacPoliciesPage() {
  const { t } = useI18n();
  const [payload, setPayload] = useState<PoliciesPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [saved, setSaved] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch("/api/admin/policies", { credentials: "include" });
      if (!r.ok) throw new Error(`load failed (${r.status})`);
      const data = (await r.json()) as PoliciesPayload;
      setPayload(data);
      setDraft(JSON.stringify(data, null, 2));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handlePublish = useCallback(async () => {
    setSubmitting(true);
    setSaved(false);
    try {
      const parsed = JSON.parse(draft) as PoliciesPayload;
      const r = await fetch("/api/admin/policies", {
        method: "PUT",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(parsed),
      });
      if (!r.ok) {
        const detail = (await r.json().catch(() => ({}))) as { detail?: string };
        throw new Error(detail.detail ?? `publish failed (${r.status})`);
      }
      setPayload((await r.json()) as PoliciesPayload);
      setSaved(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "publish failed");
    } finally {
      setSubmitting(false);
    }
  }, [draft]);

  return (
    <AdminPageShell title={t.admin.policies.title} description={t.admin.policies.description}>
      <Tabs defaultValue="view">
        <TabsList>
          <TabsTrigger value="view">{t.admin.policies.tabView}</TabsTrigger>
          <TabsTrigger value="edit">{t.admin.policies.tabEdit}</TabsTrigger>
          <TabsTrigger value="audit">{t.admin.policies.tabAudit ?? "审计"}</TabsTrigger>
        </TabsList>

        {error ? <div className="mt-2 text-sm text-destructive">{error}</div> : null}

        <TabsContent value="view">
          <Card>
            <CardHeader>
              <CardTitle>{t.admin.policies.viewTitle}</CardTitle>
              <CardDescription>{t.admin.policies.description}</CardDescription>
            </CardHeader>
            <CardContent>
              {!payload ? (
                <div className="text-sm text-muted-foreground">{t.admin.policies.loading}</div>
              ) : payload.policies.length === 0 ? (
                <div className="text-sm text-muted-foreground">{t.admin.policies.empty}</div>
              ) : (
                <div className="divide-y">
                  {payload.policies.map((p) => (
                    <div key={p.id} className="flex items-center justify-between py-2 text-sm">
                      <div>
                        <div className="font-mono font-medium">{p.id}</div>
                        <div className="text-xs text-muted-foreground">
                          {p.applies_to?.join(", ") ?? t.admin.policies.action}
                        </div>
                      </div>
                      <Badge variant={EFFECT_STYLE[p.effect] ?? "outline"}>{p.effect}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="edit">
          <Card>
            <CardHeader>
              <CardTitle>{t.admin.policies.editTitle}</CardTitle>
              <CardDescription>{t.admin.policies.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <textarea
                className="min-h-[320px] w-full rounded-md border bg-transparent p-3 font-mono text-xs"
                value={draft}
                onChange={(e) => {
                  setDraft(e.target.value);
                  setSaved(false);
                }}
                spellCheck={false}
              />
              <div className="flex items-center gap-3">
                <Button disabled={submitting} onClick={handlePublish}>
                  {submitting ? t.admin.policies.saving : t.admin.policies.save}
                </Button>
                {saved ? (
                  <span className="text-sm text-emerald-600">{t.admin.policies.saved}</span>
                ) : null}
                <Button variant="ghost" onClick={() => payload && setDraft(JSON.stringify(payload, null, 2))}>
                  {t.admin.policies.cancel}
                </Button>
              </div>
            </CardContent>
          </Card>
        <TabsContent value="audit">
          <PoliciesAuditList />
        </TabsContent>
</TabsContent>
      </Tabs>
    </AdminPageShell>
  );
}

function PoliciesAuditList() {
  const { t } = useI18n();
  const [records, setRecords] = useState<Array<{ ts: string; action: string; actor_id?: string | null; target?: string | null; details?: Record<string, unknown> | null }>>([]);
  useEffect(() => {
    void fetch("/api/admin/policies/audit", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : { records: [] }))
      .then((d) => setRecords(Array.isArray(d.records) ? d.records : []))
      .catch(() => setRecords([]));
  }, []);
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.admin.policies.auditTitle ?? "发布审计"}</CardTitle>
        <CardDescription>"发布记录"</CardDescription>
      </CardHeader>
      <CardContent>
        {records.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无发布记录。</p>
        ) : (
          <div className="space-y-2">
            {records.map((e, i) => (
              <div key={i} className="rounded-lg border px-3 py-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-muted-foreground">{e.ts}</span>
                  <Badge variant="outline">{e.action}</Badge>
                </div>
                <div className="mt-1 text-xs">
                  <span className="text-muted-foreground">actor:</span> {e.actor_id ?? "-"}
                  {" · "}<span className="text-muted-foreground">target:</span> {e.target ?? "-"}
                  {" · "}<span className="text-muted-foreground">details:</span> {JSON.stringify(e.details ?? {})}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
