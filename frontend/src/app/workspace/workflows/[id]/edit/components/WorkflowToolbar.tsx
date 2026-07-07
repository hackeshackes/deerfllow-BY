"use client";

import { ChevronDownIcon, HistoryIcon, Undo2Icon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useWorkflowVersions } from "@/core/canvas/hooks/use-workflow-versions";
import { useI18n } from "@/core/i18n/hooks";

interface WorkflowToolbarProps {
  workflowId: string | null;
  currentVersion: number;
  onRollback?: (version: number) => void;
}

/**
 * WorkflowToolbar — secondary toolbar (right of the header Save) that
 * surfaces version history and rollback. Save + Run live in the page
 * header to keep the destructive/primary actions grouped.
 *
 * Contract:
 *   - data-testid="workflow-toolbar"         root
 *   - data-testid="toolbar-history"          toggle the dropdown
 *   - data-testid="toolbar-versions"         dropdown panel
 *   - data-testid="toolbar-rollback-{n}"     per-version rollback button
 */
export function WorkflowToolbar({ workflowId, currentVersion, onRollback }: WorkflowToolbarProps) {
  const { t } = useI18n();
  const { versions, rollback, isLoading } = useWorkflowVersions(workflowId);
  const [open, setOpen] = useState(false);

  const onClickRollback = async (version: number) => {
    setOpen(false);
    if (onRollback) {
      onRollback(version);
    } else {
      await rollback(version);
    }
  };

  if (!workflowId) {
    return <div data-testid="workflow-toolbar" data-disabled="no-workflow" />;
  }

  return (
    <div className="flex items-center gap-2" data-testid="workflow-toolbar">
      <div className="relative">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          data-testid="toolbar-history"
        >
          <HistoryIcon className="size-4" />
          {t.canvasWorkflows.versionLabel} {currentVersion}
          <ChevronDownIcon className="size-3" />
        </Button>
        {open && (
          <div
            data-testid="toolbar-versions"
            className="absolute right-0 z-10 mt-1 max-h-72 w-64 overflow-auto rounded border bg-white shadow"
          >
            {isLoading ? (
              <p className="p-3 text-xs text-gray-500">{t.common.loading}</p>
            ) : versions.length === 0 ? (
              <p className="p-3 text-xs text-gray-500">No history yet.</p>
            ) : (
              <ul>
                {[...versions].reverse().map((v) => {
                  const isCurrent = v.version === currentVersion;
                  return (
                    <li
                      key={`${v.workflow_id}-${v.version}`}
                      data-testid="toolbar-version-row"
                      data-version={v.version}
                      className={`flex items-center justify-between border-b px-3 py-2 text-xs last:border-0 ${
                        isCurrent ? "bg-blue-50" : "hover:bg-gray-50"
                      }`}
                    >
                      <div>
                        <div className="font-medium">
                          {t.canvasWorkflows.versionLabel} {v.version}
                          {isCurrent && <span className="ml-1 text-blue-600">(current)</span>}
                        </div>
                        <div className="text-gray-500">{new Date(v.created_at).toLocaleString()}</div>
                      </div>
                      {!isCurrent && (
                        <Button
                          size="sm"
                          variant="ghost"
                          data-testid={`toolbar-rollback-${v.version}`}
                          onClick={() => void onClickRollback(v.version)}
                          className="h-6 gap-1 px-2 text-xs"
                        >
                          <Undo2Icon className="size-3" />
                          Rollback
                        </Button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
