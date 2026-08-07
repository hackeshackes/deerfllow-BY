"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/core/i18n/hooks";

import { AdminPageShell } from "./admin-page-shell";

type UsageRow = {
  id: string;
  tokens: number;
  executions: number;
  last_active_at: number | null;
};

type UsageResponse = {
  group_by: string;
  rows: UsageRow[];
  next_cursor: number | null;
  total: number;
};

const LIMITS = [25, 50, 100];

export function QuotaUsagePage() {
  const { t } = useI18n();
  const [groupBy, setGroupBy] = useState<"user" | "workspace">("user");
  const [limit, setLimit] = useState(25);
  const [cursor, setCursor] = useState(0);
  const [data, setData] = useState<UsageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(
    async (nextGroupBy = groupBy, nextLimit = limit, nextCursor = cursor) => {
      try {
        const params = new URLSearchParams({
          group_by: nextGroupBy,
          limit: String(nextLimit),
          cursor: String(nextCursor),
        });
        const r = await fetch(`/api/admin/quota/usage?${params.toString()}`, { credentials: "include" });
        if (!r.ok) throw new Error(`load failed (${r.status})`);
        setData((await r.json()) as UsageResponse);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : t.admin.quotaUsage.loadFailed);
      }
    },
    [groupBy, limit, cursor, t],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const switchGroup = (g: "user" | "workspace") => {
    setGroupBy(g);
    setCursor(0);
    void refresh(g, limit, 0);
  };

  const changeLimit = (l: number) => {
    setLimit(l);
    setCursor(0);
    void refresh(groupBy, l, 0);
  };

  const page = (delta: number) => {
    const next = Math.max(0, cursor + delta * limit);
    setCursor(next);
    void refresh(groupBy, limit, next);
  };

  return (
    <AdminPageShell title={t.admin.quotaUsage.title} description={t.admin.quotaUsage.description}>
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>{t.admin.quotaUsage.title}</CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant={groupBy === "user" ? "default" : "outline"}
                size="sm"
                onClick={() => switchGroup("user")}
              >
                {t.admin.quotaUsage.groupByUser}
              </Button>
              <Button
                variant={groupBy === "workspace" ? "default" : "outline"}
                size="sm"
                onClick={() => switchGroup("workspace")}
              >
                {t.admin.quotaUsage.groupByWorkspace}
              </Button>
            </div>
          </div>
          <CardDescription>{error ?? t.admin.quotaUsage.description}</CardDescription>
        </CardHeader>
        <CardContent>
          {!data ? (
            <div className="text-sm text-muted-foreground">{t.admin.quotaUsage.loading}</div>
          ) : data.rows.length === 0 ? (
            <div className="text-sm text-muted-foreground">{t.admin.quotaUsage.empty}</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-4">{t.admin.quotaUsage.id}</th>
                    <th className="py-2 pr-4">{t.admin.quotaUsage.tokens}</th>
                    <th className="py-2 pr-4">{t.admin.quotaUsage.executions}</th>
                    <th className="py-2">{t.admin.quotaUsage.lastActive}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((r) => (
                    <tr key={r.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-mono">{r.id}</td>
                      <td className="py-2 pr-4 tabular-nums">{r.tokens}</td>
                      <td className="py-2 pr-4 tabular-nums">{r.executions}</td>
                      <td className="py-2 text-muted-foreground">
                        {r.last_active_at ? new Date(r.last_active_at * 1000).toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-1">
              {LIMITS.map((l) => (
                <Button key={l} variant={limit === l ? "default" : "outline"} size="sm" onClick={() => changeLimit(l)}>
                  {l}
                </Button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={cursor === 0} onClick={() => page(-1)}>
                {t.admin.quotaUsage.prev}
              </Button>
              <span className="text-xs text-muted-foreground">{data ? `${data.total} rows` : ""}</span>
              <Button
                variant="outline"
                size="sm"
                disabled={!data?.next_cursor}
                onClick={() => page(1)}
              >
                {t.admin.quotaUsage.next}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </AdminPageShell>
  );
}