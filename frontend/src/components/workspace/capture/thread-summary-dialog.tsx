"use client";

import { BookmarkPlusIcon, LoaderIcon, SparklesIcon, WorkflowIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { getBackendBaseURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";

import { WorkflowDraftDialog } from "./workflow-draft-dialog";

export interface ThreadSummaryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  threadId: string;
  threadTitle?: string;
}

interface SummarizeResult {
  summary: string;
  key_points: string[];
  suggested_name: string;
}

export function ThreadSummaryDialog({
  open,
  onOpenChange,
  threadId,
  threadTitle,
}: ThreadSummaryDialogProps) {
  const { t } = useI18n();
  const router = useRouter();
  const [summary, setSummary] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showActions, setShowActions] = useState(false);
  const [showWorkflowDraft, setShowWorkflowDraft] = useState(false);

  const generateSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSummary("");
    setShowActions(false);

    try {
      const response = await fetch(
        `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/summarize`,
        { method: "POST" }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${response.status}`);
      }

      const result: SummarizeResult = await response.json();
      setSummary(result.summary || t.common.captureSummaryPlaceholder);
      setShowActions(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : t.common.captureError;
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  }, [threadId, t]);

  useEffect(() => {
    if (open && !summary && !isLoading) {
      void generateSummary();
    }
  }, [open, summary, isLoading, generateSummary]);

  const handleSaveToKnowledge = useCallback(async () => {
    if (!summary) return;
    setIsSaving(true);
    try {
      const kbResponse = await fetch(`${getBackendBaseURL()}/api/knowledge`);
      if (!kbResponse.ok) {
        throw new Error("Failed to load knowledge bases");
      }
      const kbList = await kbResponse.json();

      if (!kbList || kbList.length === 0) {
        toast.error(t.knowledge.empty);
        setIsSaving(false);
        return;
      }

      const targetKb = kbList[0];

      const saveResponse = await fetch(
        `${getBackendBaseURL()}/api/knowledge/${targetKb.id}/text`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: summary,
            title: threadTitle !== undefined && threadTitle !== "" ? threadTitle : t.pages.untitled,
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
      setIsSaving(false);
    }
  }, [summary, threadTitle, t]);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="flex flex-col sm:max-w-2xl max-h-[75vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <SparklesIcon className="size-4" />
              {t.common.captureDialogTitle}
              {threadTitle && (
                <span className="text-muted-foreground font-normal text-sm">
                  — {threadTitle}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 min-h-0 flex flex-col gap-4">
            <div className="flex-1 min-h-0">
              <label className="text-sm font-medium mb-2 block">
                {t.common.captureSummaryLabel}
              </label>
              <ScrollArea className="h-[300px] rounded-md border">
                <div className="p-3">
                  {isLoading && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <LoaderIcon className="size-4 animate-spin" />
                      <span className="text-sm">{t.common.captureGenerating}</span>
                    </div>
                  )}
                  {error && !isLoading && (
                    <div className="text-destructive text-sm">{error}</div>
                  )}
                  {!isLoading && !error && summary && (
                    <Textarea
                      className="h-full min-h-[280px] resize-none border-0 shadow-none p-0 focus-visible:ring-0"
                      value={summary}
                      onChange={(e) => setSummary(e.target.value)}
                      placeholder={t.common.captureSummaryPlaceholder}
                    />
                  )}
                  {!isLoading && !error && !summary && (
                    <div className="text-muted-foreground text-sm">
                      {t.common.captureNoMessages}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>

            {showActions && (
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSaveToKnowledge}
                  disabled={isSaving || !summary}
                >
                  {isSaving ? (
                    <LoaderIcon className="size-4 animate-spin" />
                  ) : (
                    <BookmarkPlusIcon className="size-4" />
                  )}
                  {t.common.captureSaveToKnowledge}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowWorkflowDraft(true)}
                  disabled={!summary}
                >
                  <WorkflowIcon className="size-4 mr-1" />
                  {t.common.captureCreateWorkflow}
                </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const params = new URLSearchParams();
                  if (threadTitle) params.set("title", threadTitle);
                  if (summary) params.set("prompt", summary);
                  params.set("source_thread_id", threadId);
                  router.push(`/workspace/automations/new?${params.toString()}`);
                }}
                disabled={!summary}
              >
                {t.common.captureCreateAutomation}
              </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
      <WorkflowDraftDialog
        open={showWorkflowDraft}
        onOpenChange={setShowWorkflowDraft}
        summary={summary}
        threadTitle={threadTitle}
      />
    </>
  );
}
