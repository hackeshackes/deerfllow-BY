"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { AdminPageShell } from "./admin-page-shell";

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
        if (!response.ok) throw new Error("加载 Token 统计失败");
        setData((await response.json()) as TokenUsageResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载 Token 统计失败");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [days]);

  return (
    <AdminPageShell
      title="Token 统计"
      description="查看 Token 使用量，按用户和模型维度统计分析。"
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500">统计周期：</span>
          <select
            className="rounded-lg border px-3 py-1.5 text-sm"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>最近 7 天</option>
            <option value={14}>最近 14 天</option>
            <option value={30}>最近 30 天</option>
            <option value={60}>最近 60 天</option>
            <option value={90}>最近 90 天</option>
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
        <p className="text-sm text-slate-500">正在加载...</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">总 Token</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(data?.total.total_tokens ?? 0)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">输入 Token</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(data?.total.input_tokens ?? 0)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">输出 Token</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(data?.total.output_tokens ?? 0)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">请求次数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(data?.total.request_count ?? 0)}</div>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="users" className="w-full">
            <TabsList>
              <TabsTrigger value="users">按用户</TabsTrigger>
              <TabsTrigger value="models">按模型</TabsTrigger>
            </TabsList>
            <TabsContent value="users">
              <Card>
                <CardHeader>
                  <CardTitle>用户 Token 使用量</CardTitle>
                  <CardDescription>各用户的 Token 消耗统计。</CardDescription>
                </CardHeader>
                <CardContent>
                  {(data?.by_user ?? []).length === 0 ? (
                    <p className="text-sm text-slate-500">暂无数据。</p>
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
                              <div className="text-slate-500">输入</div>
                              <div className="font-medium">{formatNumber(user.input_tokens)}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-slate-500">输出</div>
                              <div className="font-medium">{formatNumber(user.output_tokens)}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-slate-500">总计</div>
                              <div className="font-bold">{formatNumber(user.total_tokens)}</div>
                            </div>
                            <Badge variant="secondary">{user.request_count} 次</Badge>
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
                  <CardTitle>模型 Token 使用量</CardTitle>
                  <CardDescription>各模型的 Token 消耗统计。</CardDescription>
                </CardHeader>
                <CardContent>
                  {(data?.by_model ?? []).length === 0 ? (
                    <p className="text-sm text-slate-500">暂无数据。</p>
                  ) : (
                    <div className="space-y-3">
                      {data?.by_model.map((model) => (
                        <div key={model.model_name} className="flex items-center justify-between rounded-2xl border px-4 py-3">
                          <div className="font-medium">{model.model_name}</div>
                          <div className="flex items-center gap-6 text-sm">
                            <div className="text-right">
                              <div className="text-slate-500">输入</div>
                              <div className="font-medium">{formatNumber(model.input_tokens)}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-slate-500">输出</div>
                              <div className="font-medium">{formatNumber(model.output_tokens)}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-slate-500">总计</div>
                              <div className="font-bold">{formatNumber(model.total_tokens)}</div>
                            </div>
                            <Badge variant="secondary">{model.request_count} 次</Badge>
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
