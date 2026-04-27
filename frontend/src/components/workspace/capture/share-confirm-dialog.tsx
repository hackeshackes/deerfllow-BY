"use client";

import { useState } from "react";

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

export interface ShareConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceName?: string;
  itemType: "thread" | "summary" | "workflow" | "automation" | "knowledge";
  itemTitle?: string;
  onConfirm: () => void | Promise<void>;
  isLoading?: boolean;
}

export function ShareConfirmDialog({
  open,
  onOpenChange,
  workspaceName = "当前工作区",
  itemType,
  itemTitle,
  onConfirm,
  isLoading = false,
}: ShareConfirmDialogProps) {
  const { t } = useI18n();
  const [loading, setLoading] = useState(false);

  const itemTypeLabel = {
    thread: "对话",
    summary: "对话总结",
    workflow: "工作流",
    automation: "自动化",
    knowledge: "资料",
  }[itemType];

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>确认发布到 {workspaceName}</DialogTitle>
          <DialogDescription>
            {itemTitle ? (
              <p className="mt-2">
                即将发布「{itemTitle}」{itemTypeLabel}到{workspaceName}。
              </p>
            ) : (
              <p className="mt-2">即将发布此{itemTypeLabel}到{workspaceName}。</p>
            )}
            <p className="mt-2">
              发布后，{workspaceName}内的所有成员都将可以查看此{itemTypeLabel}。
            </p>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            {t.common.cancel}
          </Button>
          <Button onClick={handleConfirm} disabled={loading || isLoading}>
            {loading ? t.common.loading : "确认发布"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
