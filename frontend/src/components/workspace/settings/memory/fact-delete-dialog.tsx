"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useI18n } from "@/core/i18n/hooks";

import type { MemoryFact } from "./types";
import { truncateFactPreview } from "./utils";

interface FactDeleteDialogProps {
  factToDelete: MemoryFact | null;
  isPending: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}

export function FactDeleteDialog({
  factToDelete,
  isPending,
  onOpenChange,
  onConfirm,
}: FactDeleteDialogProps) {
  const { t } = useI18n();
  const factDeleteConfirmTitle =
    t.settings.memory.factDeleteConfirmTitle ?? "Delete this fact?";
  const factDeleteConfirmDescription =
    t.settings.memory.factDeleteConfirmDescription ??
    "This fact will be removed from memory immediately. This action cannot be undone.";
  const factPreviewLabel =
    t.settings.memory.factPreviewLabel ?? "Fact to delete";

  return (
    <Dialog open={factToDelete !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{factDeleteConfirmTitle}</DialogTitle>
          <DialogDescription>
            {factDeleteConfirmDescription}
          </DialogDescription>
        </DialogHeader>
        {factToDelete ? (
          <div className="bg-muted rounded-md border p-3 text-sm">
            <div className="text-muted-foreground mb-1 font-medium">
              {factPreviewLabel}
            </div>
            <p className="break-words">
              {truncateFactPreview(factToDelete.content)}
            </p>
          </div>
        ) : null}
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            {t.common.cancel}
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isPending}
          >
            {isPending ? t.common.loading : t.common.delete}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
