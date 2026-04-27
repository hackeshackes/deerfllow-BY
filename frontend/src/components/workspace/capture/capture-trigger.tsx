"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ThreadSummaryDialog } from "@/components/workspace/capture/thread-summary-dialog";
import { useThread } from "@/components/workspace/messages/context";
import { Tooltip } from "@/components/workspace/tooltip";
import { useI18n } from "@/core/i18n/hooks";

interface CaptureTriggerProps {
  threadId: string;
}

export function CaptureTrigger({ threadId }: CaptureTriggerProps) {
  const { t } = useI18n();
  const { thread } = useThread();
  const [dialogOpen, setDialogOpen] = useState(false);

  if (thread.messages.length === 0) {
    return null;
  }

  return (
    <>
      <Tooltip content={t.common.captureHint}>
        <Button
          className="text-muted-foreground hover:text-foreground"
          variant="ghost"
          onClick={() => setDialogOpen(true)}
        >
          <svg
            className="size-4"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
            />
          </svg>
          {t.common.capture}
        </Button>
      </Tooltip>

      <ThreadSummaryDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        threadId={threadId}
        threadTitle={thread.values?.title}
      />
    </>
  );
}
