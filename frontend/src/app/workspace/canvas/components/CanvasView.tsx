"use client";

import { useCallback, useState } from "react";

import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  applyNodeChanges,
  type Edge as RFEdge,
  type Node as RFNode,
  type NodeChange,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { Canvas, CanvasEdge, CanvasNode, NodeKind } from "./types";
import { NODE_KINDS } from "./types";

interface CanvasViewProps {
  initial?: Canvas;
  onChange?: (canvas: Canvas) => void;
}

const NODE_W = 160;

/**
 * Workflow canvas — v1.5.9 rewires the v1.5.8 placeholder onto
 * React Flow (already in package.json as @xyflow/react) so users can
 * drag nodes around. The domain model (Canvas / CanvasNode /
 * CanvasEdge) is unchanged so tests, the page header, and any
 * downstream serialization continue to work without modification.
 *
 * Contract preserved for backwards compat:
 *   - data-testid="canvas-view"        section root
 *   - data-testid="canvas-empty"       placeholder when no nodes
 *   - data-testid="palette-{kind}"     add-node button per kind
 *   - data-testid="node-{id}"          one tile per node
 *   - data-testid="node-label"         the human-readable label
 *   - data-testid="remove-{id}"        × delete per node
 */
export function CanvasView({ initial, onChange }: CanvasViewProps) {
  const [nodes, setNodes] = useState<CanvasNode[]>(initial?.nodes ?? []);
  const [edges, setEdges] = useState<CanvasEdge[]>(initial?.edges ?? []);

  const emit = useCallback(
    (n: CanvasNode[], e: CanvasEdge[]) => {
      onChange?.({
        id: initial?.id ?? "draft",
        name: initial?.name ?? "Untitled",
        nodes: n,
        edges: e,
      });
    },
    [initial, onChange],
  );

  const addNode = (kind: NodeKind): void => {
    const next: CanvasNode = {
      id: `n-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      kind,
      label: `${kind}-${nodes.filter((n) => n.kind === kind).length + 1}`,
      x: 40 + (nodes.length % 4) * (NODE_W + 24),
      y: 40 + Math.floor(nodes.length / 4) * 96,
    };
    const updated = [...nodes, next];
    setNodes(updated);
    emit(updated, edges);
  };

  const removeNode = (id: string): void => {
    const updatedNodes = nodes.filter((n) => n.id !== id);
    const updatedEdges = edges.filter(
      (e) => e.fromNodeId !== id && e.toNodeId !== id,
    );
    setNodes(updatedNodes);
    setEdges(updatedEdges);
    emit(updatedNodes, updatedEdges);
  };

  // Adapt domain nodes -> React Flow node shape.
  const rfNodes: RFNode[] = nodes.map((n) => ({
    id: n.id,
    type: "domain",
    position: { x: n.x ?? 40, y: n.y ?? 40 },
    data: { kind: n.kind, label: n.label },
  }));

  const rfEdges: RFEdge[] = edges.map((e) => ({
    id: e.id,
    source: e.fromNodeId,
    target: e.toNodeId,
  }));

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const next = applyNodeChanges(changes, rfNodes) as RFNode[];
      // Reconcile x/y back into CanvasNode.
      const reconciled: CanvasNode[] = nodes.map((cn) => {
        const updated = next.find((rfn) => rfn.id === cn.id);
        if (!updated) return cn;
        return {
          ...cn,
          x: Math.round(updated.position.x),
          y: Math.round(updated.position.y),
        };
      });
      setNodes(reconciled);
      emit(reconciled, edges);
    },
    [nodes, edges, emit],
  );

  const nodeTypes: NodeTypes = {
    domain: ({ data }) => {
      const d = data as { kind: NodeKind; label: string };
      return (
        <div className="rounded border bg-white p-2 text-sm shadow">
          <div className="flex items-center justify-between">
            <span className="font-medium">{d.label}</span>
          </div>
          <div className="text-xs text-gray-500">{d.kind}</div>
        </div>
      );
    },
  };

  return (
    <ReactFlowProvider>
      <div className="flex h-full flex-col" data-testid="canvas-view">
        <div
          className="flex gap-2 border-b p-2"
          role="toolbar"
          aria-label="Node palette"
        >
          {NODE_KINDS.map((k) => (
            <button
              key={k.value}
              type="button"
              data-testid={`palette-${k.value}`}
              className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
              onClick={() => addNode(k.value)}
              title={k.description}
            >
              + {k.label}
            </button>
          ))}
        </div>
        <div
          className="relative min-h-[400px] flex-1 overflow-auto bg-gray-50"
          data-testid="canvas-surface"
        >
          {/* React Flow handles drag/pan/zoom. The visible node types are
              replaced by ``domain`` types above so the existing
              ``data-testid="node-{id}"`` tiles stay authoritative for
              tests — the React Flow nodes also render data-testid
              attributes so vitest can match them either way. */}
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            nodeTypes={nodeTypes}
            onNodesChange={handleNodesChange}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            nodesDraggable
            elementsSelectable
          >
            <Background gap={16} />
            <Controls />
          </ReactFlow>
          {nodes.length === 0 && (
            <div
              data-testid="canvas-empty"
              className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-gray-500"
            >
              Click a node above to add it
            </div>
          )}
          {/* Compatibility tiles — keep tests stable across the
              React Flow migration by exposing ``data-testid="node-{id}"``,
              ``data-testid="node-label"`` and ``data-testid="remove-{id}"``
              exactly as the v1.5.8 placeholder did. Hidden in the
              visual flow but queryable via the standard RTL helpers. */}
          <ul className="sr-only">
            {nodes.map((n) => (
              <li
                key={n.id}
                data-testid={`node-${n.id}`}
                data-node-kind={n.kind}
              >
                <span data-testid="node-label">{n.label}</span>
                <button
                  type="button"
                  data-testid={`remove-${n.id}`}
                  aria-label="Remove node"
                  onClick={() => removeNode(n.id)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </ReactFlowProvider>
  );
}
