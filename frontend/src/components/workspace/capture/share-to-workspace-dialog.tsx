"use client";

import { Building2Icon, Loader2Icon, UserIcon } from "lucide-react";
import { useEffect, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getBackendBaseURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";

interface Workspace {
  id: string;
  name: string;
  role: string;
  default_personal: boolean;
}

interface ShareToWorkspaceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  threadId: string;
  threadTitle: string;
  currentWorkspaceId?: string;
  onShareSuccess?: () => void;
}

export function ShareToWorkspaceDialog({
  open,
  onOpenChange,
  threadId,
  threadTitle,
  currentWorkspaceId,
  onShareSuccess,
}: ShareToWorkspaceDialogProps) {
  const { t } = useI18n();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setIsLoadingWorkspaces(true);
      setError(null);
      fetch("/api/workspaces")
        .then((res) => res.json())
        .then((data) => {
          const ws = (data.workspaces as Workspace[]) || [];
          // Filter out the current workspace and personal workspaces
          const shareable = ws.filter(
            (w) => w.id !== currentWorkspaceId
          );
          setWorkspaces(shareable);
          if (shareable.length > 0) {
            setSelectedWorkspaceId(shareable[0]!.id);
          }
        })
        .catch(() => {
          setError("Failed to load workspaces");
        })
        .finally(() => {
          setIsLoadingWorkspaces(false);
        });
    }
  }, [open, currentWorkspaceId]);

  const handleShare = async () => {
    if (!selectedWorkspaceId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/visibility`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            visibility: "workspace",
            workspace_id: selectedWorkspaceId,
          }),
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to share thread");
      }

      onOpenChange(false);
      onShareSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to share thread");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>分享到工作区</DialogTitle>
          <DialogDescription>
            选择一个工作区来分享「{threadTitle}」。分享后，该工作区的成员将可以查看此对话。
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {isLoadingWorkspaces ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2Icon className="h-4 w-4 animate-spin" />
              <span>加载工作区...</span>
            </div>
          ) : workspaces.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              没有可分享的工作区。你需要先创建一个共享工作区。
            </p>
          ) : (
            <div className="space-y-2">
              <label className="text-sm font-medium">选择工作区</label>
              <Select
                value={selectedWorkspaceId}
                onValueChange={setSelectedWorkspaceId}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择一个工作区" />
                </SelectTrigger>
                <SelectContent>
                  {workspaces.map((workspace) => (
                    <SelectItem key={workspace.id} value={workspace.id}>
                      <div className="flex items-center gap-2">
                        {workspace.default_personal ? (
                          <UserIcon className="h-4 w-4" />
                        ) : (
                          <Building2Icon className="h-4 w-4" />
                        )}
                        <span>{workspace.name}</span>
                        <span className="text-muted-foreground text-xs">
                          ({workspace.role})
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {error && (
            <p className="mt-2 text-sm text-red-500">{error}</p>
          )}
        </div>

        <DialogFooter>
          <button
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
            className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors hover:bg-secondary mouse:hover:text-accent-foreground h-10 px-4 py-2 bg-secondary"
          >
            {t.common.cancel}
          </button>
          <button
            onClick={handleShare}
            disabled={
              isLoading ||
              isLoadingWorkspaces ||
              !selectedWorkspaceId ||
              workspaces.length === 0
            }
            className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
          >
            {isLoading ? (
              <>
                <Loader2Icon className="h-4 w-4 animate-spin mr-2" />
                分享中...
              </>
            ) : (
              "确认分享"
            )}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}