"use client";

import { useState } from "react";
import { BookmarkPlusIcon, LoaderIcon, SparklesIcon, WorkflowIcon, Share2Icon, MoreHorizontalIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThreadSummaryDialog } from "@/components/workspace/capture/thread-summary-dialog";
import { WorkflowDraftDialog } from "@/components/workspace/capture/workflow-draft-dialog";
import { ShareToWorkspaceDialog } from "@/components/workspace/capture/share-to-workspace-dialog";
import { useThread } from "@/components/workspace/messages/context";
import { Tooltip } from "@/components/workspace/tooltip";
import { useI18n } from "@/core/i18n/hooks";
import { getBackendBaseURL } from "@/core/config";
import { useRouter } from "next/navigation";

interface CaptureTriggerProps {
  threadId: string;
}

export function CaptureTrigger({ threadId }: CaptureTriggerProps) {
  const { t } = useI18n();
  const router = useRouter();
  const { thread } = useThread();
  const [summaryDialogOpen, setSummaryDialogOpen] = useState(false);
  const [workflowDraftOpen, setWorkflowDraftOpen] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [summaryForWorkflow, setSummaryForWorkflow] = useState("");
  const [isSavingToKnowledge, setIsSavingToKnowledge] = useState(false);

  if (thread.messages.length === 0) {
    return null;
  }

  const handleSaveToKnowledge = async () => {
    if (!summaryForWorkflow) {
      toast.error(t.common.captureError);
      return;
    }
    setIsSavingToKnowledge(true);
    try {
      const kbResponse = await fetch(`${getBackendBaseURL()}/api/knowledge`);
      if (!kbResponse.ok) {
        throw new Error("Failed to load knowledge bases");
      }
      const kbList = await kbResponse.json();
      if (!kbList || kbList.length === 0) {
        toast.error(t.knowledge.empty);
        return;
      }
      const targetKb = kbList[0];
      const saveResponse = await fetch(
        `${getBackendBaseURL()}/api/knowledge/${targetKb.id}/text`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: summaryForWorkflow,
            title: thread.values?.title || t.pages.untitled,
          }),
        }
      );
      if (!saveResponse.ok) {
        const data = await saveResponse.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to save to knowledge base");
      }
      toast.success(t.common.captureSaveSuccess);
    } catch (err) {
      const message = err instanceof Error ? err.message : t.common.captureError;
      toast.error(message);
    } finally {
      setIsSavingToKnowledge(false);
    }
  };

  const handleCreateWorkflow = () => {
    if (!summaryForWorkflow) {
      setSummaryDialogOpen(true);
      return;
    }
    setWorkflowDraftOpen(true);
  };

  const handleCreateAutomation = () => {
    const params = new URLSearchParams();
    if (thread.values?.title) params.set("title", thread.values.title);
    if (summaryForWorkflow) params.set("prompt", summaryForWorkflow);
    params.set("source_thread_id", threadId);
    router.push(`/workspace/automations/new?${params.toString()}`);
  };

  const handleShare = () => {
    setShareDialogOpen(true);
  };

  return (
    <>
      <Tooltip content={t.common.captureHint}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              className="text-muted-foreground hover:text-foreground"
              variant="ghost"
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
              <MoreHorizontalIcon className="size-3 ml-1" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onSelect={() => setSummaryDialogOpen(true)}>
              <SparklesIcon className="size-4 mr-2" />
              {t.common.captureDialogTitle}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={handleSaveToKnowledge}
              disabled={!summaryForWorkflow || isSavingToKnowledge}
            >
              {isSavingToKnowledge ? (
                <LoaderIcon className="size-4 mr-2 animate-spin" />
              ) : (
                <BookmarkPlusIcon className="size-4 mr-2" />
              )}
              {t.common.captureSaveToKnowledge}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={handleCreateWorkflow}
              disabled={!summaryForWorkflow}
            >
              <WorkflowIcon className="size-4 mr-2" />
              {t.common.captureCreateWorkflow}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={handleCreateAutomation}
              disabled={!summaryForWorkflow}
            >
              <SparklesIcon className="size-4 mr-2" />
              {t.common.captureCreateAutomation}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={handleShare}>
              <Share2Icon className="size-4 mr-2" />
              分享到空间
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </Tooltip>

      <ThreadSummaryDialog
        open={summaryDialogOpen}
        onOpenChange={setSummaryDialogOpen}
        threadId={threadId}
        threadTitle={thread.values?.title}
        onSummaryGenerated={(summary) => {
          setSummaryForWorkflow(summary);
        }}
      />

      {summaryForWorkflow && (
        <WorkflowDraftDialog
          open={workflowDraftOpen}
          onOpenChange={setWorkflowDraftOpen}
          summary={summaryForWorkflow}
          threadTitle={thread.values?.title}
        />
      )}

      <ShareToWorkspaceDialog
        open={shareDialogOpen}
        onOpenChange={setShareDialogOpen}
        threadId={threadId}
        threadTitle={thread.values?.title ?? ""}
        onShareSuccess={() => {
          toast.success("已分享到工作区");
        }}
      />
    </>
  );
}
