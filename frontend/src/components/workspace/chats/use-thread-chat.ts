"use client";

import { useParams, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { uuid } from "@/core/utils/uuid";

export function useThreadChat() {
  const { thread_id: threadIdFromPath } = useParams<{ thread_id: string }>();
  const pathname = usePathname();

  const searchParams = useSearchParams();

  // Always trust the URL for threadId - this prevents stale state issues
  // when rapidly switching between conversations
  const [threadId, setThreadIdState] = useState(() => {
    return threadIdFromPath === "new" ? uuid() : threadIdFromPath;
  });

  const [isNewThread, setIsNewThread] = useState(
    () => threadIdFromPath === "new",
  );

  // Track if we're in a new thread creation flow
  const isCreatingNewThread = useRef(false);

  const setThreadId = useCallback((newId: string | ((prev: string) => string)) => {
    if (typeof newId === "function") {
      setThreadIdState((prev) => {
        const result = newId(prev);
        isCreatingNewThread.current = false;
        return result;
      });
    } else {
      isCreatingNewThread.current = false;
      setThreadIdState(newId);
    }
  }, []);

  useEffect(() => {
    const isUrlNew = pathname.endsWith("/new");

    // If URL is /new, always create a new thread
    if (isUrlNew) {
      if (!isCreatingNewThread.current) {
        isCreatingNewThread.current = true;
        setIsNewThread(true);
        setThreadIdState(uuid());
      }
      return;
    }

    // Reset new thread creation flag
    isCreatingNewThread.current = false;

    // For non-new URLs, always trust the URL
    // Extract thread ID from path - format is /workspace/chats/{thread_id}
    const pathParts = pathname.split("/");
    const urlThreadId = pathParts[pathParts.length - 1];

    if (urlThreadId && urlThreadId !== "new") {
      setIsNewThread(false);
      setThreadIdState(urlThreadId);
    }
  }, [pathname]);

  const isMock = searchParams.get("mock") === "true";
  return { threadId, setThreadId, isNewThread, setIsNewThread, isMock };
}
