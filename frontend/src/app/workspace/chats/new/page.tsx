"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";

import { SceneSelector, type ChatScene } from "../components/SceneSelector";

const STORAGE_KEY = "micx_pending_scene";

/**
 * New chat entry point. Picking a scene stores the choice in localStorage
 * and redirects to the workspace — the chat composer picks it up to prefill
 * the system prompt / knowledge base / tool palette.
 */
export default function NewChatPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [scene, setScene] = useState<ChatScene>("free");

  const onStart = (): void => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, scene);
    }
    router.push("/workspace");
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-6" data-testid="new-chat-page">
      <header>
        <h1 className="text-2xl font-semibold">{t.chats.newChatTitle}</h1>
        <p className="text-muted-foreground text-sm">{t.chats.newChatSubtitle}</p>
      </header>

      <SceneSelector onChange={setScene} />

      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={() => router.push("/workspace/chats")}>
          {t.common.cancel}
        </Button>
        <Button
          data-testid="start-chat"
          onClick={onStart}
          disabled={!scene}
        >
          {t.chats.start}
        </Button>
      </div>
    </div>
  );
}
