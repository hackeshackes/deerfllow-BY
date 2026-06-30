export type NodeKind = "agent" | "tool" | "prompt" | "branch" | "loop";

export interface CanvasNode {
  id: string;
  kind: NodeKind;
  label: string;
  /** Optional 2-D position on the canvas (top-left corner, px). */
  x?: number;
  y?: number;
}

export interface CanvasEdge {
  id: string;
  fromNodeId: string;
  toNodeId: string;
}

export interface Canvas {
  id: string;
  name: string;
  nodes: CanvasNode[];
  edges: CanvasEdge[];
}

export const NODE_KINDS: ReadonlyArray<{
  value: NodeKind;
  label: string;
  description: string;
}> = [
  { value: "agent", label: "Agent", description: "Run a configured LLM agent" },
  { value: "tool", label: "Tool", description: "Invoke a registered tool" },
  { value: "prompt", label: "Prompt", description: "Static prompt with variables" },
  { value: "branch", label: "Branch", description: "Conditional routing" },
  { value: "loop", label: "Loop", description: "Iterate over a collection" },
];
