"use client";

import { BookmarkPlusIcon, CheckIcon, CopyIcon, LoaderIcon, SparklesIcon } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { getBackendBaseURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";

interface KnowledgeBase {
  id: string;
  name: string;
  visibility: string;
}

export interface ThreadSummaryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  threadId: string;
  threadTitle?: string;
  onSummaryGenerated?: (summary: string) => void;
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
  onSummaryGenerated,
}: ThreadSummaryDialogProps) {
  const { t } = useI18n();
  const router = useRouter();
  const [summary, setSummary] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showActions, setShowActions] = useState(false);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selectedKbId, setSelectedKbId] = useState<string>("");
  const [showKbSelect, setShowKbSelect] = useState(false);
  const [summaryCopied, setSummaryCopied] = useState(false);
  const [currentSummaryForSave, setCurrentSummaryForSave] = useState<string>("");

  const generateSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSummary("");
    setShowActions(false);
    setSummaryCopied(false);

    try {
      const response = await fetch(
        `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/summarize`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ max_messages: 50 }),
        },
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${response.status}`);
      }

      const result: SummarizeResult = await response.json();
      const generatedSummary = result.summary || t.common.captureSummaryPlaceholder;
      setSummary(generatedSummary);
      setCurrentSummaryForSave(generatedSummary);
      setShowActions(true);
      onSummaryGenerated?.(generatedSummary);
    } catch (err) {
      const message = err instanceof Error ? err.message : typeof err === "object" && err !== null ? JSON.stringify(err) : t.common.captureError;
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  }, [threadId, t, onSummaryGenerated]);

  useEffect(() => {
    if (open && !summary && !isLoading) {
      void generateSummary();
    }
    if (!open) {
      setShowKbSelect(false);
    }
  }, [open, summary, isLoading, generateSummary]);

  useEffect(() => {
    if (showKbSelect) {
      void fetchKnowledgeBases();
    }
  }, [showKbSelect]);

  const fetchKnowledgeBases = async () => {
    try {
      const response = await fetch(`${getBackendBaseURL()}/api/knowledge`);
      if (!response.ok) throw new Error("Failed to load");
      const data = await response.json();
      setKnowledgeBases(data);
      if (data.length > 0) {
        setSelectedKbId(data[0].id);
      }
    } catch (err) {
      toast.error(t.knowledge.empty);
    }
  };

  const handleCopy = useCallback(() => {
    void navigator.clipboard.writeText(currentSummaryForSave);
    setSummaryCopied(true);
    toast.success(t.clipboard.copiedToClipboard);
    setTimeout(() => setSummaryCopied(false), 2000);
  }, [currentSummaryForSave, t]);

  const handleSaveToKnowledge = async () => {
    if (!currentSummaryForSave || !selectedKbId) return;
    setIsSaving(true);
    try {
      const saveResponse = await fetch(
        `${getBackendBaseURL()}/api/knowledge/${selectedKbId}/text`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: currentSummaryForSave,
            title: threadTitle ?? t.pages.untitled,
          }),
        }
      );
      if (!saveResponse.ok) {
        const data = await saveResponse.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to save");
      }
      toast.success(t.common.captureSaveSuccess);
      setShowKbSelect(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : t.common.captureError;
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleGoToKnowledge = () => {
    if (selectedKbId) {
      router.push(`/workspace/knowledge/${selectedKbId}`);
    }
  };

  const handleCreateAutomation = () => {
    const params = new URLSearchParams();
    if (threadTitle) params.set("title", threadTitle);
    if (currentSummaryForSave) params.set("prompt", currentSummaryForSave);
    params.set("source_thread_id", threadId);
    router.push(`/workspace/automations/new?${params.toString()}`);
  };

  return (
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
                {!isLoading && !error && currentSummaryForSave && (
                  <Textarea
                    className="h-full min-h-[280px] resize-none border-0 shadow-none p-0 focus-visible:ring-0"
                    value={currentSummaryForSave}
                    onChange={(e) => setCurrentSummaryForSave(e.target.value)}
                    placeholder={t.common.captureSummaryPlaceholder}
                  />
                )}
                {!isLoading && !error && !currentSummaryForSave && (
                  <div className="text-muted-foreground text-sm">
                    {t.common.captureNoMessages}
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>

          {showActions && !showKbSelect && (
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowKbSelect(true)}
              >
                <BookmarkPlusIcon className="size-4 mr-1" />
                {t.common.captureSaveToKnowledge}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
              >
                {summaryCopied ? (
                  <CheckIcon className="size-4 mr-1" />
                ) : (
                  <CopyIcon className="size-4 mr-1" />
                )}
                {summaryCopied ? "已复制" : "复制"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCreateAutomation}
              >
                <SparklesIcon className="size-4 mr-1" />
                {t.common.captureCreateAutomation}
              </Button>
            </div>
          )}

          {showActions && showKbSelect && (
            <div className="space-y-3 p-3 border rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">保存到资料库</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowKbSelect(false)}
                >
                  返回
                </Button>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">选择资料库</label>
                <Select value={selectedKbId} onValueChange={setSelectedKbId}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择一个资料库" />
                  </SelectTrigger>
                  <SelectContent>
                    {knowledgeBases.map((kb) => (
                      <SelectItem key={kb.id} value={kb.id}>
                        {kb.name} ({kb.visibility})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleSaveToKnowledge}
                  disabled={isSaving || !selectedKbId}
                >
                  {isSaving ? (
                    <LoaderIcon className="size-4 animate-spin mr-1" />
                  ) : (
                    <BookmarkPlusIcon className="size-4 mr-1" />
                  )}
                  {t.common.captureSaveToKnowledge}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleGoToKnowledge}
                  disabled={!selectedKbId}
                >
                  查看资料库
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
