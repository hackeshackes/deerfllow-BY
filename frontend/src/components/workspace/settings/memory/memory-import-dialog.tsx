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
import { formatTimeAgo } from "@/core/utils/datetime";

import type { PendingImport } from "./types";

interface MemoryImportDialogProps {
  pendingImport: PendingImport | null;
  isPending: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}

export function MemoryImportDialog({
  pendingImport,
  isPending,
  onOpenChange,
  onConfirm,
}: MemoryImportDialogProps) {
  const { t } = useI18n();

  return (
    <Dialog open={pendingImport !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t.settings.memory.importConfirmTitle}</DialogTitle>
          <DialogDescription>
            {t.settings.memory.importConfirmDescription}
          </DialogDescription>
        </DialogHeader>
        {pendingImport ? (
          <div className="bg-muted rounded-md border p-3 text-sm">
            <div>
              <span className="text-muted-foreground">
                {t.settings.memory.importFileLabel}:
              </span>{" "}
              {pendingImport.fileName}
            </div>
            <div>
              <span className="text-muted-foreground">
                {t.settings.memory.markdown.facts}:
              </span>{" "}
              {pendingImport.memory.facts.length}
            </div>
            <div>
              <span className="text-muted-foreground">
                {t.common.lastUpdated}:
              </span>{" "}
              {pendingImport.memory.lastUpdated
                ? formatTimeAgo(pendingImport.memory.lastUpdated)
                : "-"}
            </div>
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
          <Button onClick={onConfirm} disabled={isPending}>
            {isPending ? t.common.loading : t.common.import}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
