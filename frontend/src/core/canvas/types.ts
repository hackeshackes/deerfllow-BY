// Types aligned with backend WorkflowResponse / NodeKind / WorkflowStatus.
// backend/app/gateway/canvas/routers/workflows.py: WorkflowResponse,
// models.py: NodeKind / WorkflowStatus.

export type NodeKind = "agent" | "tool" | "prompt" | "branch" | "loop";

export type WorkflowStatus = "draft" | "published" | "archived";

export interface CanvasNodeConfig {
  template?: string;
  iterations?: number;
  condition?: string;
  prompt?: string;
  tool_name?: string;
  args?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface CanvasNode {
  id: string;
  kind: NodeKind;
  config: CanvasNodeConfig;
  position: [number, number];
}

export interface CanvasEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  /** "true" / "false" routing label for BRANCH; null otherwise. */
  condition: string | null;
}

export interface Workflow {
  id: string;
  name: string;
  workspace_id: string;
  status: WorkflowStatus;
  version: number;
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowVersion {
  workflow_id: string;
  version: number;
  created_at: string;
  snapshot: Workflow;
}

export interface ExecutionStep {
  node_id: string;
  status: "ok" | "failed" | "skipped";
  started_at: string;
  ended_at: string;
  outputs: Record<string, unknown>;
  error: string | null;
}

export interface ExecutionResult {
  workflow_id: string;
  workflow_version: number;
  outputs: Record<string, Record<string, unknown>>;
  steps: ExecutionStep[];
  total_tokens: number;
  failed_node_id: string | null;
}

export const NODE_KINDS: ReadonlyArray<{ value: NodeKind; label: string; description: string }> = [
  { value: "prompt", label: "Prompt", description: "Static prompt with {{var}} interpolation" },
  { value: "agent", label: "Agent", description: "Delegate to a DeerFlow agent" },
  { value: "tool", label: "Tool", description: "Invoke a registered tool" },
  { value: "branch", label: "Branch", description: "Conditional routing (var op value)" },
  { value: "loop", label: "Loop", description: "Iterate a body N times" },
];
