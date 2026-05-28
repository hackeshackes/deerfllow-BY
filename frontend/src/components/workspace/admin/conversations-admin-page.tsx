"use client";

import { MessageCircleIcon, UserIcon, UsersIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { AdminPageShell } from "@/components/workspace/admin/admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

type ChannelThread = {
  channel: string;
  chat_id: string;
  topic_id: string | null;
  thread_id: string;
  user_id: string;
  micx_user_id: string | null;
  micx_workspace_id: string | null;
  created_at: number;
  updated_at: number;
};

const channelLabels: Record<string, string> = {
  feishu: "Feishu",
  slack: "Slack",
  telegram: "Telegram",
  wecom: "WeCom",
  dingtalk: "DingTalk",
};

const channelIcons: Record<string, string> = {
  feishu: "📱",
  slack: "💬",
  telegram: "✈️",
  wecom: "💼",
  dingtalk: "📌",
};

export function ConversationsAdminPage() {
  const { t } = useI18n();
  const [threads, setThreads] = useState<ChannelThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assignTarget, setAssignTarget] = useState<ChannelThread | null>(null);
  const [assigning, setAssigning] = useState(false);
  const [micxUserId, setMicxUserId] = useState("");
  const [micxWorkspaceId, setMicxWorkspaceId] = useState("");

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/channels/threads");
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail ?? t.admin.conversations.loadFailed);
      }
      const data = (await res.json()) as { channels: ChannelThread[] };
      setThreads(data.channels);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.admin.conversations.loadFailed);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [t.admin.conversations.loadFailed]);

  function openAssignDialog(thread: ChannelThread) {
    setAssignTarget(thread);
    setMicxUserId(thread.micx_user_id ?? "");
    setMicxWorkspaceId(thread.micx_workspace_id ?? "");
  }

  async function handleAssign() {
    if (!assignTarget) return;
    setAssigning(true);
    try {
      const res = await fetch(`/api/channels/threads/${assignTarget.thread_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          micx_user_id: micxUserId.trim() || null,
          micx_workspace_id: micxWorkspaceId.trim() || null,
        }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail ?? t.admin.conversations.assignFailed);
      }
      toast.success(t.admin.conversations.assignSuccess);
      setAssignTarget(null);
      await loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t.admin.conversations.assignFailed);
    } finally {
      setAssigning(false);
    }
  }

  const groupedThreads: Record<string, ChannelThread[]> = {};
  for (const t_local of threads) {
    (groupedThreads[t_local.channel] ??= []).push(t_local);
  }

  return (
    <AdminPageShell title={t.admin.conversations.title} description={t.admin.conversations.description}>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageCircleIcon className="size-5" />
              {t.admin.conversations.title} ({threads.length})
            </CardTitle>
            <CardDescription>IM conversations initiated through Feishu, Slack, Telegram, etc.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-sm text-slate-500">{t.admin.conversations.loading}</div>
            ) : error ? (
              <div className="py-8 text-center text-sm text-red-500">{error}</div>
            ) : threads.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-500">{t.admin.conversations.noConversations}</div>
            ) : (
              <div className="space-y-6">
                {Object.entries(groupedThreads).map(([channel, channelThreads]) => (
                  <div key={channel}>
                    <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-600">
                      <span>{channelIcons[channel] ?? "💬"}</span>
                      <span>{channelLabels[channel] ?? channel}</span>
                      <Badge variant="secondary">{channelThreads.length}</Badge>
                    </div>
                    <div className="space-y-2">
                      {channelThreads.map((thread) => (
                        <div
                          key={`${thread.chat_id}-${thread.topic_id ?? ""}`}
                          className="flex items-center justify-between rounded-2xl border p-4"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-mono text-sm">
                                {thread.chat_id.length > 20
                                  ? `${thread.chat_id.slice(0, 20)}...`
                                  : thread.chat_id}
                              </span>
                              {thread.topic_id && (
                                <Badge variant="outline" className="text-xs">
                                  {t.admin.conversations.topic}: {thread.topic_id.slice(0, 12)}...
                                </Badge>
                              )}
                              <Badge variant="outline" className="text-xs">
                                {t.admin.conversations.thread}: {thread.thread_id.slice(0, 12)}...
                              </Badge>
                            </div>
                            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
                              <span className="flex items-center gap-1">
                                <UserIcon className="size-3" />
                                {thread.user_id || t.admin.conversations.unassigned}
                              </span>
                              {thread.micx_user_id && (
                                <span className="flex items-center gap-1 text-emerald-600">
                                  <UsersIcon className="size-3" />
                                  {t.admin.conversations.micxUser}: {thread.micx_user_id}
                                </span>
                              )}
                              {thread.micx_workspace_id && (
                                <span className="flex items-center gap-1 text-blue-600">
                                  <UsersIcon className="size-3" />
                                  {t.admin.conversations.workspace}: {thread.micx_workspace_id}
                                </span>
                              )}
                              <span>{new Date(thread.created_at * 1000).toLocaleDateString()}</span>
                            </div>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openAssignDialog(thread)}
                            className="ml-4 shrink-0"
                          >
                            {t.admin.conversations.assignOwnership}
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={assignTarget !== null} onOpenChange={() => setAssignTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.admin.conversations.assignOwnership}</DialogTitle>
            <DialogDescription>
              Assign IM conversation to MicX user and workspace.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t.admin.conversations.micxUserId}</label>
              <Input
                placeholder="Leave empty for unassigned"
                value={micxUserId}
                onChange={(e) => setMicxUserId(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t.admin.conversations.micxWorkspaceId}</label>
              <Input
                placeholder="Leave empty for unassigned"
                value={micxWorkspaceId}
                onChange={(e) => setMicxWorkspaceId(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignTarget(null)}>
              {t.admin.channels.cancel}
            </Button>
            <Button onClick={() => void handleAssign()} disabled={assigning}>
              {assigning ? t.admin.conversations.assigning : t.admin.conversations.assign}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}