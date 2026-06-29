"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import { useThreads } from "@/core/threads/hooks";
import { pathOfThread, titleOfThread } from "@/core/threads/utils";
import type { ThreadSource } from "@/core/threads/source";
import { formatTimeAgo } from "@/core/utils/datetime";

import {
  PartitionedChatList,
  type ChatItem,
} from "./components/PartitionedChatList";

const DEFAULT_SOURCE: ThreadSource = "manual";

export default function ChatsPage() {
  const { t } = useI18n();
  const { data: threads } = useThreads();
  const [search, setSearch] = useState("");

  useEffect(() => {
    document.title = `${t.pages.chats} - ${t.pages.appName}`;
  }, [t.pages.chats, t.pages.appName]);

  const chatItems: ChatItem[] = useMemo(() => {
    return (threads ?? []).map((thread) => ({
      id: thread.thread_id,
      title: titleOfThread(thread),
      // Default unknown / older threads to `manual` so the partition UI
      // still has somewhere to put them.
      source: (thread.source ?? DEFAULT_SOURCE) as ThreadSource,
      updatedAt: thread.updated_at ?? "",
    }));
  }, [threads]);

  const filteredItems = useMemo(() => {
    if (!search) return chatItems;
    const q = search.toLowerCase();
    return chatItems.filter((c) => c.title.toLowerCase().includes(q));
  }, [chatItems, search]);

  return (
    <WorkspaceContainer>
      <WorkspaceHeader></WorkspaceHeader>
      <WorkspaceBody>
        <div className="flex size-full flex-col">
          <header className="flex shrink-0 items-center justify-center pt-8">
            <Input
              type="search"
              className="h-12 w-full max-w-(--container-width-md) text-xl"
              placeholder={t.chats.searchChats}
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </header>
          <main className="min-h-0 flex-1">
            <ScrollArea className="size-full py-4">
              <div className="mx-auto flex size-full max-w-(--container-width-md) flex-col">
                <PartitionedChatList
                  chats={filteredItems}
                  renderItem={(item) => (
                    <Link href={pathOfThread(item.id)}>
                      <div className="flex flex-col gap-1">
                        <span className="font-medium">{item.title}</span>
                        <span className="text-muted-foreground text-xs">
                          [{item.source}]
                          {item.updatedAt
                            ? ` · ${formatTimeAgo(item.updatedAt)}`
                            : ""}
                        </span>
                      </div>
                    </Link>
                  )}
                />
              </div>
            </ScrollArea>
          </main>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
