"use client";

import { CopyIcon, LoaderIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/core/i18n/hooks";
import { createCustomSkill } from "@/core/skills/api";

export interface WorkflowDraftDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  summary: string;
  threadTitle?: string;
}

function buildSkillMd(params: {
  name: string;
  description: string;
  promptTemplate: string;
}): string {
  const { name, description, promptTemplate } = params;
  const safeName = name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "") || "my-workflow";
  return `---
name: ${safeName}
description: ${description}
---

# ${name}

${description}

## Workflow

### Step 1: Understand the Task

${promptTemplate}

### Step 2: Execute

Follow the instructions above and deliver the result in a clear format.

### Step 3: Present

Present the result with a brief summary.
`;
}

export function WorkflowDraftDialog({
  open,
  onOpenChange,
  summary,
  threadTitle,
}: WorkflowDraftDialogProps) {
  const { t } = useI18n();
  const [name, setName] = useState(threadTitle ?? "");
  const [description, setDescription] = useState("");
  const [promptTemplate, setPromptTemplate] = useState(summary);
  const [visibility, setVisibility] = useState<"private" | "workspace">("private");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setName(threadTitle ?? "");
      setDescription("");
      setPromptTemplate(summary);
      setVisibility("private");
    }
  }, [open, summary, threadTitle]);

  const skillContent = buildSkillMd({ name, description, promptTemplate });

  const handleSave = useCallback(async () => {
    if (!name.trim()) {
      toast.error(t.common.captureWorkflowNamePlaceholder);
      return;
    }
    setIsSaving(true);
    try {
      await createCustomSkill({
        name: name.trim(),
        content: skillContent,
      });
      toast.success(t.common.captureWorkflowSaveSuccess);
      onOpenChange(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : t.common.captureWorkflowSaveError;
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  }, [name, skillContent, t, onOpenChange]);

  const handleCopy = useCallback(() => {
    void navigator.clipboard.writeText(skillContent);
    toast.success(t.clipboard.copiedToClipboard);
  }, [skillContent, t]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex flex-col sm:max-w-2xl max-h-[85vh]">
        <DialogHeader>
          <DialogTitle>{t.common.captureCreateWorkflow}</DialogTitle>
        </DialogHeader>

        <div className="flex-1 min-h-0 flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="text-sm font-medium block mb-1">
                {t.common.captureWorkflowName}
              </label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t.common.captureWorkflowNamePlaceholder}
              />
            </div>

            <div className="col-span-2">
              <label className="text-sm font-medium block mb-1">
                {t.common.captureWorkflowDescription}
              </label>
              <Input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t.common.captureWorkflowDescriptionPlaceholder}
              />
            </div>

            <div className="col-span-2">
              <label className="text-sm font-medium block mb-1">
                {t.common.captureWorkflowVisibility}
              </label>
              <Select
                value={visibility}
                onValueChange={(v) => setVisibility(v as "private" | "workspace")}
              >
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="private">{t.common.private}</SelectItem>
                  <SelectItem value="workspace">{t.common.workspace}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex-1 min-h-0">
            <label className="text-sm font-medium block mb-1">
              {t.common.captureWorkflowPrompt}
            </label>
            <ScrollArea className="h-[300px] rounded-md border">
              <div className="p-3">
                <Textarea
                  className="h-full min-h-[280px] resize-none border-0 shadow-none p-0 focus-visible:ring-0 font-mono text-sm"
                  value={promptTemplate}
                  onChange={(e) => setPromptTemplate(e.target.value)}
                />
              </div>
            </ScrollArea>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={handleCopy} disabled={isSaving}>
            <CopyIcon className="size-4 mr-1" />
            {t.common.captureWorkflowCopy}
          </Button>
          <Button size="sm" onClick={handleSave} disabled={isSaving}>
            {isSaving ? <LoaderIcon className="size-4 animate-spin mr-1" /> : null}
            {t.common.captureWorkflowSave}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
