// API client for /api/workflows (canvas backend) — v1.6.x.
// Mirrors backend/app/gateway/canvas/routers/workflows.py.
// All mutating methods require the current session cookie (browser fetch
// carries it automatically).

import type { ExecutionResult, Workflow, WorkflowVersion } from "./types";

export interface WorkflowCreateBody {
  name: string;
  workspace_id: string;
  status?: "draft" | "published" | "archived";
  nodes?: Array<{
    id: string;
    kind: "agent" | "tool" | "prompt" | "branch" | "loop";
    config?: Record<string, unknown>;
    position?: [number, number];
  }>;
  edges?: Array<{
    id: string;
    source_node_id: string;
    target_node_id: string;
    condition?: string | null;
  }>;
}

export interface WorkflowUpdateBody {
  name?: string;
  status?: "draft" | "published" | "archived";
  nodes?: WorkflowCreateBody["nodes"];
  edges?: WorkflowCreateBody["edges"];
}

export interface ExecuteBody {
  inputs: Record<string, unknown>;
  workspace_id: string;
  estimated_tokens?: number;
}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = await res.json();
    } catch {
      // body wasn't JSON; fall through
    }
    throw new Error(`canvas API ${res.status}: ${JSON.stringify(detail)}`);
  }
  return (await res.json()) as T;
}

export const canvasApi = {
  async list(workspaceId: string): Promise<{ workflows: Workflow[] }> {
    return asJson(
      await fetch(`/api/workflows?workspace_id=${encodeURIComponent(workspaceId)}`, {
        credentials: "include",
      }),
    );
  },

  async get(workflowId: string): Promise<Workflow> {
    return asJson(
      await fetch(`/api/workflows/${encodeURIComponent(workflowId)}`, { credentials: "include" }),
    );
  },

  async create(body: WorkflowCreateBody): Promise<Workflow> {
    return asJson(
      await fetch("/api/workflows", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    );
  },

  async update(workflowId: string, body: WorkflowUpdateBody): Promise<Workflow> {
    return asJson(
      await fetch(`/api/workflows/${encodeURIComponent(workflowId)}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    );
  },

  async remove(workflowId: string): Promise<{ success: boolean }> {
    return asJson(
      await fetch(`/api/workflows/${encodeURIComponent(workflowId)}`, {
        method: "DELETE",
        credentials: "include",
      }),
    );
  },

  async listVersions(workflowId: string): Promise<{ versions: WorkflowVersion[] }> {
    return asJson(
      await fetch(`/api/workflows/${encodeURIComponent(workflowId)}/versions`, {
        credentials: "include",
      }),
    );
  },

  async rollback(workflowId: string, version: number): Promise<Workflow> {
    return asJson(
      await fetch(
        `/api/workflows/${encodeURIComponent(workflowId)}/rollback/${encodeURIComponent(String(version))}`,
        { method: "POST", credentials: "include" },
      ),
    );
  },

  async execute(workflowId: string, body: ExecuteBody): Promise<ExecutionResult> {
    return asJson(
      await fetch(`/api/workflows/${encodeURIComponent(workflowId)}/execute`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    );
  },
};
