"use client";

import {
  Download,
  FileJson,
  FileText,
  MoreHorizontal,
  Pencil,
  Share2,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";
import { ShareToWorkspaceDialog } from "@/components/workspace/capture/share-to-workspace-dialog";
import {
  exportThreadAsJSON,
  exportThreadAsMarkdown,
} from "@/core/threads/export";
import {
  useDeleteThread,
  useRenameThread,
  useUpdateThreadVisibility,
  useThreads,
} from "@/core/threads/hooks";
import type { AgentThread, AgentThreadState } from "@/core/threads/types";
import { pathOfThread, titleOfThread } from "@/core/threads/utils";
import { env } from "@/env";
import { isIMEComposing } from "@/lib/ime";

type ThreadSource = "manual" | "automation" | "channel";

function readMetadataString(
  thread: AgentThread,
  key: string,
): string | undefined {
  const value = thread.metadata?.[key];
  return typeof value === "string" && value.trim() ? value : undefined;
}

function sourceOfThread(thread: AgentThread): ThreadSource {
  const source = readMetadataString(thread, "source");
  if (source === "automation" || readMetadataString(thread, "task_id")) {
    return "automation";
  }
  if (source === "channel" || readMetadataString(thread, "channel")) {
    return "channel";
  }
  return "manual";
}

function sourceLabelOfThread(thread: AgentThread): string | null {
  const source = sourceOfThread(thread);
  if (source === "automation") return "自动化";
  if (source === "channel") return readMetadataString(thread, "channel") ?? "外部渠道";
  return null;
}

function isWorkspaceThread(thread: AgentThread): boolean {
  return readMetadataString(thread, "visibility") === "workspace";
}

export function RecentChatList() {
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  const { thread_id: threadIdFromPath } = useParams<{ thread_id: string }>();
  const { data: threads = [] } = useThreads();
  const { mutate: deleteThread } = useDeleteThread();
  const { mutate: renameThread } = useRenameThread();
  const { mutateAsync: updateThreadVisibility } = useUpdateThreadVisibility();
  const [sessionUserId, setSessionUserId] = useState<string | null>(null);

  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renameThreadId, setRenameThreadId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [shareThreadId, setShareThreadId] = useState<string | null>(null);
  const [shareThreadTitle, setShareThreadTitle] = useState<string>("");
  const [shareCurrentWorkspaceId, setShareCurrentWorkspaceId] = useState<string | undefined>();

  useEffect(() => {
    async function loadSession() {
      try {
        const response = await fetch("/api/session/me");
        if (!response.ok) return;
        const payload = (await response.json()) as { id: string };
        setSessionUserId(payload.id);
      } catch {
        // ignore session lookup failures in sidebar
      }
    }
    void loadSession();
  }, []);

  const handleDelete = useCallback(
    (threadId: string) => {
      deleteThread({ threadId });
      if (threadId === threadIdFromPath) {
        const threadIndex = threads.findIndex((t) => t.thread_id === threadId);
        let nextThreadId = "new";
        if (threadIndex > -1) {
          if (threads[threadIndex + 1]) {
            nextThreadId = threads[threadIndex + 1]!.thread_id;
          } else if (threads[threadIndex - 1]) {
            nextThreadId = threads[threadIndex - 1]!.thread_id;
          }
        }
        void router.push(`/workspace/chats/${nextThreadId}`);
      }
    },
    [deleteThread, router, threadIdFromPath, threads],
  );

  const handleRenameClick = useCallback(
    (threadId: string, currentTitle: string) => {
      setRenameThreadId(threadId);
      setRenameValue(currentTitle);
      setRenameDialogOpen(true);
    },
    [],
  );

  const handleRenameSubmit = useCallback(() => {
    if (renameThreadId && renameValue.trim()) {
      renameThread({ threadId: renameThreadId, title: renameValue.trim() });
      setRenameDialogOpen(false);
      setRenameThreadId(null);
      setRenameValue("");
    }
  }, [renameThread, renameThreadId, renameValue]);

  const handleShareClick = useCallback(
    (threadId: string, threadTitle: string, currentWorkspaceId?: string) => {
      setShareThreadId(threadId);
      setShareThreadTitle(threadTitle);
      setShareCurrentWorkspaceId(currentWorkspaceId);
      setShareDialogOpen(true);
    },
    []
  );

  const handleShareSuccess = useCallback(() => {
    toast.success("已分享到工作区");
  }, []);

  const handleMakePrivate = useCallback(
    async (threadId: string) => {
      try {
        await updateThreadVisibility({ threadId, visibility: "private" });
        toast.success("已切换为私有对话");
      } catch {
        toast.error("切换私有失败");
      }
    },
    [updateThreadVisibility],
  );

  const handleExport = useCallback(
    async (thread: AgentThread, format: "markdown" | "json") => {
      try {
        const response = await fetch(
          `${window.location.origin}/api/threads/${encodeURIComponent(thread.thread_id)}/state`,
        );
        if (!response.ok) {
          throw new Error("Failed to load thread state");
        }
        const state = (await response.json()) as { values?: AgentThreadState };
        const messages = state.values?.messages ?? [];
        if (messages.length === 0) {
          toast.error(t.conversation.noMessages);
          return;
        }
        if (format === "markdown") {
          exportThreadAsMarkdown(thread, messages);
        } else {
          exportThreadAsJSON(thread, messages);
        }
        toast.success(t.common.exportSuccess);
      } catch {
        toast.error("Failed to export conversation");
      }
    },
    [t],
  );

  if (threads.length === 0) {
    return null;
  }
  const manualThreads = threads.filter(
    (thread) => sourceOfThread(thread) === "manual",
  );
  const automationThreads = threads.filter(
    (thread) => sourceOfThread(thread) === "automation",
  );
  const channelThreads = threads.filter(
    (thread) => sourceOfThread(thread) === "channel",
  );
  const sections = [
    { title: "最近继续", threads: manualThreads },
    { title: "自动化结果", threads: automationThreads },
    { title: "外部渠道", threads: channelThreads },
  ].filter((section) => section.threads.length > 0);

  return (
    <>
      <SidebarGroup>
        <SidebarGroupLabel>
          {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY !== "true"
            ? t.sidebar.recentChats
            : t.sidebar.demoChats}
        </SidebarGroupLabel>
        <SidebarGroupContent className="group-data-[collapsible=icon]:pointer-events-none group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0">
          <SidebarMenu>
            <div className="flex w-full flex-col gap-3">
              {sections.map((section) => (
                <div key={section.title} className="space-y-1">
                  <div className="text-muted-foreground px-2 text-[11px] font-medium tracking-wide">
                    {section.title}
                  </div>
                  <div className="flex flex-col gap-1">
                    {section.threads.map((thread) => {
                const isActive = pathOfThread(thread.thread_id) === pathname;
                const visibility = (thread.metadata?.visibility as string | undefined) === "private" ? "private" : "workspace";
                const isThreadOwner = thread.metadata?.owner_user_id === sessionUserId;
                const workspaceId = typeof thread.metadata?.workspace_id === "string" ? thread.metadata.workspace_id : "";
                const sourceLabel = sourceLabelOfThread(thread);
                return (
                  <SidebarMenuItem
                    key={thread.thread_id}
                    className="group/side-menu-item"
                  >
                    <SidebarMenuButton isActive={isActive} asChild>
                      <div>
                      <div className="flex w-full items-center gap-1.5">
                        <Link
                          className="text-muted-foreground min-w-0 flex-1 truncate group-hover/side-menu-item:overflow-hidden"
                          href={pathOfThread(thread.thread_id)}
                        >
                          {titleOfThread(thread)}
                        </Link>
                        <span className="inline-flex shrink-0 items-center gap-1">
                          <Badge variant={visibility === "private" ? "outline" : "default"} className="text-[10px]">
                            {visibility === "private" ? "私有" : "已共享"}
                          </Badge>
                          {sourceLabel && (
                            <Badge variant="secondary" className="text-[10px]">
                              {sourceLabel}
                            </Badge>
                          )}
                          {!sourceLabel && isWorkspaceThread(thread) && !isThreadOwner && (
                            <Badge variant="secondary" className="text-[10px]">
                              团队
                            </Badge>
                          )}
                        </span>
                      </div>
                        {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY !== "true" && isThreadOwner && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <SidebarMenuAction
                                showOnHover
                                className="bg-background/50 hover:bg-background"
                              >
                                <MoreHorizontal />
                                <span className="sr-only">{t.common.more}</span>
                              </SidebarMenuAction>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent
                              className="w-48 rounded-lg"
                              side={"right"}
                              align={"start"}
                            >
                              <DropdownMenuItem
                                onSelect={() =>
                                  handleRenameClick(
                                    thread.thread_id,
                                    titleOfThread(thread),
                                  )
                                }
                              >
                                <Pencil className="text-muted-foreground" />
                                <span>{t.common.rename}</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onSelect={() => handleShareClick(thread.thread_id, titleOfThread(thread), workspaceId)}
                              >
                                <Share2 className="text-muted-foreground" />
                                <span>共享到工作区</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onSelect={() => handleMakePrivate(thread.thread_id)}
                                disabled={visibility === "private"}
                              >
                                <Share2 className="text-muted-foreground" />
                                <span>设为私有</span>
                              </DropdownMenuItem>
                              <DropdownMenuSub>
                                <DropdownMenuSubTrigger>
                                  <Download className="text-muted-foreground" />
                                  <span>{t.common.export}</span>
                                </DropdownMenuSubTrigger>
                                <DropdownMenuSubContent>
                                  <DropdownMenuItem
                                    onSelect={() =>
                                      handleExport(thread, "markdown")
                                    }
                                  >
                                    <FileText className="text-muted-foreground" />
                                    <span>{t.common.exportAsMarkdown}</span>
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onSelect={() =>
                                      handleExport(thread, "json")
                                    }
                                  >
                                    <FileJson className="text-muted-foreground" />
                                    <span>{t.common.exportAsJSON}</span>
                                  </DropdownMenuItem>
                                </DropdownMenuSubContent>
                              </DropdownMenuSub>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onSelect={() => handleDelete(thread.thread_id)}
                              >
                                <Trash2 className="text-muted-foreground" />
                                <span>{t.common.delete}</span>
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </div>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      {/* Rename Dialog */}
      <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t.common.rename}</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              placeholder={t.common.rename}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !isIMEComposing(e)) {
                  e.preventDefault();
                  handleRenameSubmit();
                }
              }}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRenameDialogOpen(false)}
            >
              {t.common.cancel}
            </Button>
            <Button onClick={handleRenameSubmit}>{t.common.save}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ShareToWorkspaceDialog
        open={shareDialogOpen}
        onOpenChange={setShareDialogOpen}
        threadId={shareThreadId ?? ""}
        threadTitle={shareThreadTitle}
        currentWorkspaceId={shareCurrentWorkspaceId}
        onShareSuccess={handleShareSuccess}
      />
    </>
  );
}
