"use client";

import { useId } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/core/i18n/hooks";

import type { FactFormState, MemoryFact } from "./types";

interface FactEditorDialogProps {
  open: boolean;
  factToEdit: MemoryFact | null;
  factForm: FactFormState;
  setFactForm: (
    updater: (current: FactFormState) => FactFormState,
  ) => void;
  isPending: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: () => void;
}

export function FactEditorDialog({
  open,
  factToEdit,
  factForm,
  setFactForm,
  isPending,
  onOpenChange,
  onSave,
}: FactEditorDialogProps) {
  const { t } = useI18n();
  const factContentInputId = useId();
  const factCategoryInputId = useId();
  const factConfidenceInputId = useId();
  const factConfidenceHintId = useId();

  const addFactTitle = t.settings.memory.addFactTitle;
  const editFactTitle = t.settings.memory.editFactTitle;
  const factContentLabel = t.settings.memory.factContentLabel;
  const factCategoryLabel = t.settings.memory.factCategoryLabel;
  const factConfidenceLabel = t.settings.memory.factConfidenceLabel;
  const factContentPlaceholder = t.settings.memory.factContentPlaceholder;
  const factCategoryPlaceholder = t.settings.memory.factCategoryPlaceholder;
  const factConfidenceHint = t.settings.memory.factConfidenceHint;
  const factSave = t.settings.memory.factSave;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {factToEdit ? editFactTitle : addFactTitle}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <label
              className="text-sm font-medium"
              htmlFor={factContentInputId}
            >
              {factContentLabel}
            </label>
            <Textarea
              id={factContentInputId}
              value={factForm.content}
              onChange={(event) =>
                setFactForm((current) => ({
                  ...current,
                  content: event.target.value,
                }))
              }
              placeholder={factContentPlaceholder}
              rows={4}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label
                className="text-sm font-medium"
                htmlFor={factCategoryInputId}
              >
                {factCategoryLabel}
              </label>
              <Input
                id={factCategoryInputId}
                value={factForm.category}
                onChange={(event) =>
                  setFactForm((current) => ({
                    ...current,
                    category: event.target.value,
                  }))
                }
                placeholder={factCategoryPlaceholder}
              />
            </div>

            <div className="space-y-2">
              <label
                className="text-sm font-medium"
                htmlFor={factConfidenceInputId}
              >
                {factConfidenceLabel}
              </label>
              <Input
                id={factConfidenceInputId}
                aria-describedby={factConfidenceHintId}
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={factForm.confidence}
                onChange={(event) =>
                  setFactForm((current) => ({
                    ...current,
                    confidence: event.target.value,
                  }))
                }
              />
              <div
                className="text-muted-foreground text-xs"
                id={factConfidenceHintId}
              >
                {factConfidenceHint}
              </div>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            {t.common.cancel}
          </Button>
          <Button onClick={onSave} disabled={isPending}>
            {isPending ? t.common.loading : factSave}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
