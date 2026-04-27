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
  feishu: "飞书",
  slack: "Slack",
  telegram: "Telegram",
  wecom: "企业微信",
  dingtalk: "钉钉",
};

const channelIcons: Record<string, string> = {
  feishu: "📱",
  slack: "💬",
  telegram: "✈️",
  wecom: "💼",
  dingtalk: "📌",
};

export function ConversationsAdminPage() {
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
        throw new Error(data?.detail ?? "加载会话失败");
      }
      const data = (await res.json()) as { channels: ChannelThread[] };
      setThreads(data.channels);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载会话失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

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
        throw new Error(data?.detail ?? "分配失败");
      }
      toast.success("会话分配成功");
      setAssignTarget(null);
      await loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "分配失败");
    } finally {
      setAssigning(false);
    }
  }

  const groupedThreads: Record<string, ChannelThread[]> = {};
  for (const t of threads) {
    (groupedThreads[t.channel] ??= []).push(t);
  }

  return (
    <AdminPageShell title="会话管理" description="查看和管理所有 IM 渠道发起的会话，设置用户和工作区归属。">
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageCircleIcon className="size-5" />
              所有 IM 会话 ({threads.length})
            </CardTitle>
            <CardDescription>通过飞书、Slack、Telegram 等渠道发起的会话。管理员可分配归属。</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-sm text-slate-500">加载中...</div>
            ) : error ? (
              <div className="py-8 text-center text-sm text-red-500">{error}</div>
            ) : threads.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-500">暂无 IM 会话</div>
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
                                  topic: {thread.topic_id.slice(0, 12)}...
                                </Badge>
                              )}
                              <Badge variant="outline" className="text-xs">
                                thread: {thread.thread_id.slice(0, 12)}...
                              </Badge>
                            </div>
                            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
                              <span className="flex items-center gap-1">
                                <UserIcon className="size-3" />
                                {thread.user_id || "未关联"}
                              </span>
                              {thread.micx_user_id && (
                                <span className="flex items-center gap-1 text-emerald-600">
                                  <UsersIcon className="size-3" />
                                  MicX 用户: {thread.micx_user_id}
                                </span>
                              )}
                              {thread.micx_workspace_id && (
                                <span className="flex items-center gap-1 text-blue-600">
                                  <UsersIcon className="size-3" />
                                  工作区: {thread.micx_workspace_id}
                                </span>
                              )}
                              <span>{new Date(thread.created_at * 1000).toLocaleDateString("zh-CN")}</span>
                            </div>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openAssignDialog(thread)}
                            className="ml-4 shrink-0"
                          >
                            分配归属
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
            <DialogTitle>分配会话归属</DialogTitle>
            <DialogDescription>
              将 IM 会话分配给 MicX 用户和工作区。分配后可让用户在自己的线程列表中看到该对话。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">MicX 用户 ID（可选）</label>
              <Input
                placeholder="留空表示未分配"
                value={micxUserId}
                onChange={(e) => setMicxUserId(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">MicX 工作区 ID（可选）</label>
              <Input
                placeholder="留空表示未分配"
                value={micxWorkspaceId}
                onChange={(e) => setMicxWorkspaceId(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignTarget(null)}>
              取消
            </Button>
            <Button onClick={() => void handleAssign()} disabled={assigning}>
              {assigning ? "分配中..." : "确认分配"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}
