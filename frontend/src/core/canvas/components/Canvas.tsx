"use client";

import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  applyEdgeChanges,
  applyNodeChanges,
  type Edge as RFEdge,
  type EdgeChange,
  type Node as RFNode,
  type NodeChange,
  type NodeMouseHandler,
  type NodeTypes,
} from "@xyflow/react";
import { useCallback, useEffect, useState } from "react";

import "@xyflow/react/dist/style.css";

import type { CanvasEdge, CanvasNode, NodeKind } from "../types";
import { NODE_KINDS } from "../types";

interface CanvasProps {
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  onNodesChange: (next: CanvasNode[]) => void;
  onEdgesChange: (next: CanvasEdge[]) => void;
  onSelectNode: (id: string | null) => void;
  selectedNodeId: string | null;
  /** Optional click handler invoked when a node is selected (separate from selection state). */
  onNodeDoubleClick?: (id: string) => void;
}

const NODE_W = 180;

/**
 * Canvas — the React Flow surface that renders workflow nodes and edges
 * with bidirectional reconciliation between the domain shape
 * (CanvasNode / CanvasEdge) and React Flow's internal shape.
 *
 * Contract (kept stable from v1.5.9):
 *   - data-testid="canvas-view"        section root
 *   - data-testid="canvas-empty"       placeholder when no nodes
 *   - data-testid="canvas-surface"     React Flow container
 *   - data-testid="node-{id}"          per-node tile
 *   - data-testid="node-label"         the node's display label
 *   - data-testid="node-remove-{id}"   × delete per node
 *   - data-testid="edge-{id}"          per-edge SVG group
 */
export function Canvas(props: CanvasProps) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}

function CanvasInner({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onSelectNode,
  selectedNodeId,
  onNodeDoubleClick,
}: CanvasProps) {
  const [rfNodes, setRfNodes] = useState<RFNode[]>(() => toRfNodes(nodes));
  const [rfEdges, setRfEdges] = useState<RFEdge[]>(() => toRfEdges(edges));

  // Reconcile external -> internal when the parent passes new domain state.
  // Without this the canvas can drift away from the source of truth (the page).
  useEffect(() => {
    setRfNodes(toRfNodes(nodes));
  }, [nodes]);

  useEffect(() => {
    setRfEdges(toRfEdges(edges));
  }, [edges]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const nextRf = applyNodeChanges(changes, rfNodes) as RFNode[];
      setRfNodes(nextRf);
      onNodesChange(reconcile(nodes, nextRf));
    },
    [nodes, rfNodes, onNodesChange],
  );

  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const nextRf = applyEdgeChanges(changes, rfEdges) as RFEdge[];
      setRfEdges(nextRf);
      onEdgesChange(
        nextRf.map((e) => ({
          id: e.id,
          source_node_id: e.source,
          target_node_id: e.target,
          condition: typeof e.label === "string" ? e.label : null,
        })),
      );
    },
    [rfEdges, onEdgesChange],
  );

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      onSelectNode(node.id);
    },
    [onSelectNode],
  );

  const handleNodeDoubleClick: NodeMouseHandler = useCallback(
    (_, node) => {
      onNodeDoubleClick?.(node.id);
    },
    [onNodeDoubleClick],
  );

  const handlePaneClick = useCallback(() => {
    onSelectNode(null);
  }, [onSelectNode]);

  const nodeTypes: NodeTypes = {
    domain: ({ id, data, selected }) => {
      const d = data as { kind: NodeKind; label: string };
      const isSelected = selected || id === selectedNodeId;
      return (
        <div
          data-testid={`node-${id}`}
          data-node-kind={d.kind}
          data-selected={isSelected ? "true" : "false"}
          className={`rounded border bg-white p-2 text-xs shadow ${
            isSelected ? "border-blue-500 ring-2 ring-blue-200" : "border-gray-300"
          }`}
          style={{ width: NODE_W }}
        >
          <div className="flex items-center justify-between">
            <span data-testid="node-label" className="font-medium">
              {d.label}
            </span>
            <button
              type="button"
              data-testid={`node-remove-${id}`}
              onClick={(e) => {
                e.stopPropagation();
                onEdgesChange(
                  edges.filter((edge) => edge.source_node_id !== id && edge.target_node_id !== id),
                );
                onNodesChange(nodes.filter((n) => n.id !== id));
                if (selectedNodeId === id) onSelectNode(null);
              }}
              className="text-gray-400 hover:text-red-500"
              aria-label="remove"
            >
              ×
            </button>
          </div>
          <div className="text-gray-500">{d.kind}</div>
        </div>
      );
    },
  };

  if (nodes.length === 0) {
    return (
      <div
        className="relative min-h-[400px] flex-1 overflow-auto bg-gray-50"
        data-testid="canvas-view"
      >
        <div
          data-testid="canvas-empty"
          className="absolute inset-0 flex items-center justify-center text-sm text-gray-400"
        >
          {NODE_KINDS.length} node types available. Use the palette to add one.
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-[400px] flex-1 overflow-auto bg-gray-50" data-testid="canvas-view">
      <div data-testid="canvas-surface" className="h-full w-full">
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          nodeTypes={nodeTypes}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onNodeClick={handleNodeClick}
          onNodeDoubleClick={handleNodeDoubleClick}
          onPaneClick={handlePaneClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          nodesDraggable
          elementsSelectable
        >
          <Background gap={16} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}

function toRfNodes(nodes: CanvasNode[]): RFNode[] {
  return nodes.map((n) => ({
    id: n.id,
    type: "domain",
    position: { x: n.position[0], y: n.position[1] },
    data: { kind: n.kind, label: `${n.kind}-${n.id.slice(-4)}` },
  }));
}

function toRfEdges(edges: CanvasEdge[]): RFEdge[] {
  return edges.map((e) => ({
    id: e.id,
    source: e.source_node_id,
    target: e.target_node_id,
    ...(e.condition ? { label: e.condition } : {}),
  }));
}

function reconcile(domain: CanvasNode[], rf: RFNode[]): CanvasNode[] {
  return domain.map((cn) => {
    const updated = rf.find((rfn) => rfn.id === cn.id);
    if (!updated) return cn;
    return {
      ...cn,
      position: [Math.round(updated.position.x), Math.round(updated.position.y)],
    };
  });
}
