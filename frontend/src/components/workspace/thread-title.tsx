import type { BaseStream } from "@langchain/langgraph-sdk";
import { useEffect, useState } from "react";

import { useI18n } from "@/core/i18n/hooks";
import type { AgentThreadState } from "@/core/threads";

import { useThreadChat } from "./chats";
import { FlipDisplay } from "./flip-display";

export function ThreadTitle({
  threadId,
  thread,
}: {
  className?: string;
  threadId: string;
  thread: BaseStream<AgentThreadState>;
}) {
  const { t } = useI18n();
  const { isNewThread } = useThreadChat();
  const [overrideTitle, setOverrideTitle] = useState<string | null>(null);

  useEffect(() => {
    function handleThreadTitleUpdated(event: Event) {
      const detail = (event as CustomEvent<{ threadId?: string; title?: string }>).detail;
      if (detail?.threadId === threadId && detail.title) {
        setOverrideTitle(detail.title);
      }
    }

    window.addEventListener("micx-thread-title-updated", handleThreadTitleUpdated as EventListener);
    return () => {
      window.removeEventListener("micx-thread-title-updated", handleThreadTitleUpdated as EventListener);
    };
  }, [threadId]);

  useEffect(() => {
    let _title = t.pages.untitled;

    if (overrideTitle) {
      _title = overrideTitle;
    } else if (thread.values?.title) {
      _title = thread.values.title;
    } else if (isNewThread) {
      _title = t.pages.newChat;
    }
    if (thread.isThreadLoading) {
      document.title = `Loading... - ${t.pages.appName}`;
    } else {
      document.title = `${_title} - ${t.pages.appName}`;
    }
  }, [
    isNewThread,
    t.pages.newChat,
    t.pages.untitled,
    t.pages.appName,
    overrideTitle,
    thread.isThreadLoading,
    thread.values,
    thread.values.title,
  ]);

  const displayTitle = overrideTitle ?? thread.values?.title;

  if (!displayTitle) {
    return null;
  }
  return (
    <FlipDisplay uniqueKey={threadId}>
      {displayTitle ?? "Untitled"}
    </FlipDisplay>
  );
}
