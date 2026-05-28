"use client";

import { BrainIcon, Loader2Icon, SearchIcon } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AdminPageShell } from "@/components/workspace/admin/admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

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
  const { t } = useI18n();
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
        throw new Error(data?.detail ?? t.admin.memory.loadFailed);
      }
      const data = (await response.json()) as MemoryData;
      setMemoryData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.admin.memory.loadFailed);
    } finally {
      setLoading(false);
    }
  }

  function renderMemorySection() {
    if (!memoryData?.memory) {
      return <div className="py-8 text-center text-sm text-slate-500">{t.admin.memory.noMemoryData}</div>;
    }

    const memory = memoryData.memory;
    const hasContext = memory.context && memory.context.length > 0;
    const hasFacts = memory.facts && memory.facts.length > 0;

    return (
      <div className="space-y-6">
        {memory.last_updated && (
          <div className="text-sm text-slate-400">
            {t.admin.memory.lastUpdated}: {new Date(memory.last_updated).toLocaleString()}
          </div>
        )}

        {memory.system_prompt_context && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t.admin.memory.systemPromptContext}</CardTitle>
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
              <CardTitle className="text-base">{t.admin.memory.facts} ({memory.facts!.length})</CardTitle>
              <CardDescription>{t.admin.memory.userFactsPreferences}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {memory.facts!.map((fact, idx) => (
                  <div key={idx} className="flex items-start gap-3 rounded-lg border p-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="text-xs">{fact.category}</Badge>
                        <Badge variant="outline" className="text-xs">
                          {t.admin.memory.factConfidence}: {fact.confidence.toFixed(2)}
                        </Badge>
                        {fact.source && (
                          <span className="text-xs text-slate-400">{t.admin.memory.factSource}: {fact.source}</span>
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
              <CardTitle className="text-base">{t.admin.memory.context} ({memory.context!.length})</CardTitle>
              <CardDescription>{t.admin.memory.userContextInfo}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {memory.context!.map((ctx, idx) => (
                  <div key={idx} className="flex items-start gap-3 rounded-lg border p-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="text-xs">{ctx.category}</Badge>
                        <Badge variant="outline" className="text-xs">
                          {t.admin.memory.factConfidence}: {ctx.confidence.toFixed(2)}
                        </Badge>
                        {ctx.source && (
                          <span className="text-xs text-slate-400">{t.admin.memory.factSource}: {ctx.source}</span>
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
          <div className="py-8 text-center text-sm text-slate-500">{t.admin.memory.noMemoryData}</div>
        )}
      </div>
    );
  }

  return (
    <AdminPageShell
      title={t.admin.memory.title}
      description={t.admin.memory.description}
    >
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SearchIcon className="size-5" />
              {t.admin.memory.searchUserMemory}
            </CardTitle>
            <CardDescription>
              {t.admin.memory.searchDescription}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Input
                placeholder={t.admin.memory.userIdPlaceholder}
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void handleSearch()}
                className="max-w-sm"
              />
              <Button onClick={() => void handleSearch()} disabled={loading || !userId.trim()}>
                {loading ? <Loader2Icon className="size-4 animate-spin" /> : <SearchIcon className="size-4" />}
                {t.admin.memory.search}
              </Button>
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}

            {searched && !loading && !memoryData && !error && (
              <div className="text-sm text-slate-500">{t.admin.memory.noDataFound}</div>
            )}
          </CardContent>
        </Card>

        {memoryData && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BrainIcon className="size-5" />
                {t.admin.memory.userMemoryData}
              </CardTitle>
              <CardDescription>
                {t.admin.memory.userId}: {memoryData.user_id}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {renderMemorySection()}
            </CardContent>
          </Card>
        )}

        {!searched && (
          <div className="text-center text-sm text-slate-400 py-8">
            {t.admin.memory.enterUserId}
          </div>
        )}
      </div>
    </AdminPageShell>
  );
}