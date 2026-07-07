// useWorkflows — list + create + update + delete workflows for a workspace.
// Pure React 19 hooks; no external state lib. Aligned with /api/workflows.

import { useCallback, useEffect, useState } from "react";

import { canvasApi, type WorkflowCreateBody, type WorkflowUpdateBody } from "../api";
import type { Workflow } from "../types";

export interface UseWorkflowsResult {
  workflows: Workflow[];
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  create: (body: WorkflowCreateBody) => Promise<Workflow>;
  update: (id: string, body: WorkflowUpdateBody) => Promise<Workflow>;
  remove: (id: string) => Promise<void>;
}

export function useWorkflows(workspaceId: string | null | undefined): UseWorkflowsResult {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    if (!workspaceId) {
      setWorkflows([]);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const { workflows: items } = await canvasApi.list(workspaceId);
      setWorkflows(items);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const create = useCallback(
    async (body: WorkflowCreateBody) => {
      const wf = await canvasApi.create(body);
      setWorkflows((prev) => [...prev, wf]);
      return wf;
    },
    [],
  );

  const update = useCallback(async (id: string, body: WorkflowUpdateBody) => {
    const wf = await canvasApi.update(id, body);
    setWorkflows((prev) => prev.map((w) => (w.id === id ? wf : w)));
    return wf;
  }, []);

  const remove = useCallback(
    async (id: string) => {
      await canvasApi.remove(id);
      setWorkflows((prev) => prev.filter((w) => w.id !== id));
    },
    [],
  );

  return { workflows, isLoading, error, refresh, create, update, remove };
}
