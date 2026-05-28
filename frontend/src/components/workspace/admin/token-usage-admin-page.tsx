"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { AdminPageShell } from "./admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

type TokenUsageSummary = {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  request_count: number;
};

type UserTokenUsage = {
  user_id: string;
  email: string | null;
  name: string | null;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  request_count: number;
};

type ModelTokenUsage = {
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  request_count: number;
};

type TokenUsageResponse = {
  period_start: string | null;
  period_end: string | null;
  total: TokenUsageSummary;
  by_user: UserTokenUsage[];
  by_model: ModelTokenUsage[];
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export function TokenUsageAdminPage() {
  const { t } = useI18n();
  const [data, setData] = useState<TokenUsageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/admin/token-usage?days=${days}`);
        if (!response.ok) throw new Error(t.admin.tokenUsage.loadFailed);
        setData((await response.json()) as TokenUsageResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : t.admin.tokenUsage.loadFailed);
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [days, t.admin.tokenUsage.loadFailed]);

  return (
    <AdminPageShell
      title={t.admin.tokenUsage.title}
      description={t.admin.tokenUsage.description}
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500">{t.admin.tokenUsage.period}：</span>
          <select
            className="rounded-lg border px-3 py-1.5 text-sm"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>{t.admin.tokenUsage.last7Days}</option>
            <option value={14}>{t.admin.tokenUsage.last14Days}</option>
            <option value={30}>{t.admin.tokenUsage.last30Days}</option>
            <option value={60}>{t.admin.tokenUsage.last60Days}</option>
            <option value={90}>{t.admin.tokenUsage.last90Days}</option>
          </select>
        </div>
        {data?.period_start && (
          <span className="text-sm text-slate-400">
            {new Date(data.period_start).toLocaleDateString()} ~ {new Date(data.period_end ?? "").toLocaleDateString()}
          </span>
        )}
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {loading ? (
        <p className="text-sm text-slate-500">{t.admin.tokenUsage.loading}</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">{t.admin.tokenUsage.totalToken}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(data?.total.total_tokens ?? 0)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">{t.admin.tokenUsage.inputToken}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(data?.total.input_tokens ?? 0)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">{t.admin.tokenUsage.outputToken}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(data?.total.output_tokens ?? 0)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">{t.admin.tokenUsage.requestCount}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(data?.total.request_count ?? 0)}</div>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="users" className="w-full">
            <TabsList>
              <TabsTrigger value="users">{t.admin.tokenUsage.byUser}</TabsTrigger>
              <TabsTrigger value="models">{t.admin.tokenUsage.byModel}</TabsTrigger>
            </TabsList>
            <TabsContent value="users">
              <Card>
                <CardHeader>
                  <CardTitle>{t.admin.tokenUsage.userTokenUsage}</CardTitle>
                  <CardDescription>{t.admin.tokenUsage.userTokenUsageDescription}</CardDescription>
                </CardHeader>
                <CardContent>
                  {(data?.by_user ?? []).length === 0 ? (
                    <p className="text-sm text-slate-500">{t.admin.tokenUsage.noData}</p>
                  ) : (
                    <div className="space-y-3">
                      {data?.by_user.map((user) => (
                        <div key={user.user_id} className="flex items-center justify-between rounded-2xl border px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div>
                              <div className="font-medium">{user.name ?? user.email ?? user.user_id}</div>
                              {user.email && <div className="text-sm text-slate-500">{user.email}</div>}
                            </div>
                          </div>
                          <div className="flex items-center gap-6 text-sm">
                            <div className="text-right">
                              <div className="text-slate-500">{t.admin.tokenUsage.input}</div>
                              <div className="font-medium">{formatNumber(user.input_tokens)}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-slate-500">{t.admin.tokenUsage.output}</div>
                              <div className="font-medium">{formatNumber(user.output_tokens)}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-slate-500">{t.admin.tokenUsage.total}</div>
                              <div className="font-bold">{formatNumber(user.total_tokens)}</div>
                            </div>
                            <Badge variant="secondary">{user.request_count} {t.admin.tokenUsage.times}</Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="models">
              <Card>
                <CardHeader>
                  <CardTitle>{t.admin.tokenUsage.modelTokenUsage}</CardTitle>
                  <CardDescription>{t.admin.tokenUsage.modelTokenUsageDescription}</CardDescription>
                </CardHeader>
                <CardContent>
                  {(data?.by_model ?? []).length === 0 ? (
                    <p className="text-sm text-slate-500">{t.admin.tokenUsage.noData}</p>
                  ) : (
                    <div className="space-y-3">
                      {data?.by_model.map((model) => (
                        <div key={model.model_name} className="flex items-center justify-between rounded-2xl border px-4 py-3">
                          <div className="font-medium">{model.model_name}</div>
                          <div className="flex items-center gap-6 text-sm">
                            <div className="text-right">
                              <div className="text-slate-500">{t.admin.tokenUsage.input}</div>
                              <div className="font-medium">{formatNumber(model.input_tokens)}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-slate-500">{t.admin.tokenUsage.output}</div>
                              <div className="font-medium">{formatNumber(model.output_tokens)}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-slate-500">{t.admin.tokenUsage.total}</div>
                              <div className="font-bold">{formatNumber(model.total_tokens)}</div>
                            </div>
                            <Badge variant="secondary">{model.request_count} {t.admin.tokenUsage.times}</Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </AdminPageShell>
  );
}