"use client";

import { useCallback, useEffect, useState } from "react";

import { loadTasks, type Task } from "./api";

export interface UseScheduledTasksOptions {
  enabled?: boolean;
}

export interface UseScheduledTasksResult {
  tasks: Task[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useScheduledTasks(
  options: UseScheduledTasksOptions = {},
): UseScheduledTasksResult {
  const { enabled = true } = options;
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchTasks = useCallback(async () => {
    if (!enabled) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await loadTasks();
      setTasks(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to load tasks"));
    } finally {
      setIsLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void fetchTasks();
  }, [fetchTasks]);

  return {
    tasks,
    isLoading,
    error,
    refetch: fetchTasks,
  };
}