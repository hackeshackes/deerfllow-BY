// useWorkflowVersions — load + rollback versions for a workflow.

import { useCallback, useEffect, useState } from "react";

import { canvasApi } from "../api";
import type { WorkflowVersion } from "../types";

export interface UseWorkflowVersionsResult {
  versions: WorkflowVersion[];
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  rollback: (version: number) => Promise<void>;
}

export function useWorkflowVersions(workflowId: string | null | undefined): UseWorkflowVersionsResult {
  const [versions, setVersions] = useState<WorkflowVersion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    if (!workflowId) {
      setVersions([]);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const { versions: items } = await canvasApi.listVersions(workflowId);
      setVersions(items);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setIsLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const rollback = useCallback(
    async (version: number) => {
      if (!workflowId) return;
      await canvasApi.rollback(workflowId, version);
      await refresh();
    },
    [workflowId, refresh],
  );

  return { versions, isLoading, error, refresh, rollback };
}
