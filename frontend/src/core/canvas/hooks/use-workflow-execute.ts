// useWorkflowExecute — POST /api/workflows/{id}/execute with quota pre-check
// handled by the backend (returns 429 with QUOTA_EXCEEDED when hard mode
// blocks). Surfaces { isRunning, result, error }.

import { useCallback, useState } from "react";

import { canvasApi, type ExecuteBody } from "../api";
import type { ExecutionResult } from "../types";

export interface UseWorkflowExecuteResult {
  isRunning: boolean;
  result: ExecutionResult | null;
  error: Error | null;
  run: (workflowId: string, body: ExecuteBody) => Promise<ExecutionResult | null>;
  reset: () => void;
}

export function useWorkflowExecute(): UseWorkflowExecuteResult {
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const run = useCallback(
    async (workflowId: string, body: ExecuteBody): Promise<ExecutionResult | null> => {
      setIsRunning(true);
      setError(null);
      try {
        const out = await canvasApi.execute(workflowId, body);
        setResult(out);
        return out;
      } catch (e) {
        setError(e instanceof Error ? e : new Error(String(e)));
        return null;
      } finally {
        setIsRunning(false);
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { isRunning, result, error, run, reset };
}
