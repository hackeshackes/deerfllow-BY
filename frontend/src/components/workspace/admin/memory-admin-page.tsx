"use client";

import { BrainIcon, ChevronRightIcon, Loader2Icon, SearchIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AdminPageShell } from "@/components/workspace/admin/admin-page-shell";

type MemoryData = {
  user_id: string;
  memory: {
    context?: Array<{ category: string; content: string; confidence: number; source?: string }>;
    facts?: Array<{ fact: string; category: string; confidence: number; source?: string }>;
    history?: unknown[];
    system_prompt_context?: string;
    last_updated?: string;
  };
};

export function MemoryAdminPage() {
  const [userId, setUserId] = useState("");
  const [memoryData, setMemoryData] = useState<MemoryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function handleSearch() {
    if (!userId.trim()) return;
    setLoading(true);
    setError(null);
    setMemoryData(null);
    setSearched(true);
    try {
      const response = await fetch(`/api/admin/memory/users/${userId.trim()}`);
      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail ?? "加载记忆失败");
      }
      const data = (await response.json()) as MemoryData;
      setMemoryData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载记忆失败");
    } finally {
      setLoading(false);
    }
  }

  function renderMemorySection() {
    if (!memoryData?.memory) {
      return <div className="py-8 text-center text-sm text-slate-500">暂无记忆数据</div>;
    }

    const memory = memoryData.memory;
    const hasContext = memory.context && memory.context.length > 0;
    const hasFacts = memory.facts && memory.facts.length > 0;

    return (
      <div className="space-y-6">
        {memory.last_updated && (
          <div className="text-sm text-slate-400">
            最后更新: {new Date(memory.last_updated).toLocaleString("zh-CN")}
          </div>
        )}

        {memory.system_prompt_context && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">System Prompt Context</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">
                {memory.system_prompt_context}
              </pre>
            </CardContent>
          </Card>
        )}

        {hasFacts && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Facts ({memory.facts!.length})</CardTitle>
              <CardDescription>用户事实和偏好</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {memory.facts!.map((fact, idx) => (
                  <div key={idx} className="flex items-start gap-3 rounded-lg border p-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="text-xs">{fact.category}</Badge>
                        <Badge variant="outline" className="text-xs">
                          置信度: {fact.confidence.toFixed(2)}
                        </Badge>
                        {fact.source && (
                          <span className="text-xs text-slate-400">来源: {fact.source}</span>
                        )}
                      </div>
                      <p className="text-sm">{fact.fact}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {hasContext && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Context ({memory.context!.length})</CardTitle>
              <CardDescription>用户上下文信息</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {memory.context!.map((ctx, idx) => (
                  <div key={idx} className="flex items-start gap-3 rounded-lg border p-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="text-xs">{ctx.category}</Badge>
                        <Badge variant="outline" className="text-xs">
                          置信度: {ctx.confidence.toFixed(2)}
                        </Badge>
                        {ctx.source && (
                          <span className="text-xs text-slate-400">来源: {ctx.source}</span>
                        )}
                      </div>
                      <p className="text-sm">{ctx.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {!hasFacts && !hasContext && !memory.system_prompt_context && (
          <div className="py-8 text-center text-sm text-slate-500">暂无记忆数据</div>
        )}
      </div>
    );
  }

  return (
    <AdminPageShell
      title="记忆管理"
      description="查看指定用户的记忆数据（上下文、事实、历史）"
    >
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SearchIcon className="size-5" />
              查询用户记忆
            </CardTitle>
            <CardDescription>
              输入用户ID查看该用户的完整记忆数据
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Input
                placeholder="输入用户 ID"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void handleSearch()}
                className="max-w-sm"
              />
              <Button onClick={() => void handleSearch()} disabled={loading || !userId.trim()}>
                {loading ? <Loader2Icon className="size-4 animate-spin" /> : <SearchIcon className="size-4" />}
                查询
              </Button>
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}

            {searched && !loading && !memoryData && !error && (
              <div className="text-sm text-slate-500">未找到该用户的记忆数据</div>
            )}
          </CardContent>
        </Card>

        {memoryData && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BrainIcon className="size-5" />
                用户记忆数据
              </CardTitle>
              <CardDescription>
                用户ID: {memoryData.user_id}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {renderMemorySection()}
            </CardContent>
          </Card>
        )}

        {!searched && (
          <div className="text-center text-sm text-slate-400 py-8">
            请输入用户 ID 开始查询
          </div>
        )}
      </div>
    </AdminPageShell>
  );
}