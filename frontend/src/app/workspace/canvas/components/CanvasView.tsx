"use client";

import { useState } from "react";

import type { Canvas, CanvasEdge, CanvasNode, NodeKind } from "./types";
import { NODE_KINDS } from "./types";

interface CanvasViewProps {
  initial?: Canvas;
  onChange?: (canvas: Canvas) => void;
}

const NODE_W = 160;
const NODE_H = 64;

/**
 * Lightweight workflow canvas — renders nodes and edges as absolute
 * positioned divs/lines inside a scrollable area.
 *
 * v1.5.8 ships the visual scaffold only. Editing (drag, draw edges,
 * connect nodes) is delegated to v1.5.9 with React Flow.
 */
export function CanvasView({ initial, onChange }: CanvasViewProps) {
  const [nodes, setNodes] = useState<CanvasNode[]>(initial?.nodes ?? []);
  const [edges, setEdges] = useState<CanvasEdge[]>(initial?.edges ?? []);

  const addNode = (kind: NodeKind): void => {
    const next: CanvasNode = {
      id: `n-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      kind,
      label: `${kind}-${nodes.filter((n) => n.kind === kind).length + 1}`,
      x: 40 + (nodes.length % 4) * (NODE_W + 24),
      y: 40 + Math.floor(nodes.length / 4) * (NODE_H + 24),
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

  const emit = (n: CanvasNode[], e: CanvasEdge[]): void => {
    onChange?.({ id: initial?.id ?? "draft", name: initial?.name ?? "Untitled", nodes: n, edges: e });
  };

  return (
    <div
      className="flex h-full flex-col"
      data-testid="canvas-view"
    >
      <div className="flex gap-2 border-b p-2" role="toolbar" aria-label="Node palette">
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
        {/* Edges: draw simple lines between node centers. */}
        <svg
          className="pointer-events-none absolute inset-0"
          width="2000"
          height="2000"
        >
          {edges.map((e) => {
            const from = nodes.find((n) => n.id === e.fromNodeId);
            const to = nodes.find((n) => n.id === e.toNodeId);
            if (!from || !to) return null;
            const fx = (from.x ?? 0) + NODE_W / 2;
            const fy = (from.y ?? 0) + NODE_H / 2;
            const tx = (to.x ?? 0) + NODE_W / 2;
            const ty = (to.y ?? 0) + NODE_H / 2;
            return (
              <line
                key={e.id}
                data-testid={`edge-${e.id}`}
                x1={fx}
                y1={fy}
                x2={tx}
                y2={ty}
                stroke="#3b82f6"
                strokeWidth={2}
              />
            );
          })}
        </svg>
        {nodes.map((n) => (
          <div
            key={n.id}
            data-testid={`node-${n.id}`}
            data-node-kind={n.kind}
            className="absolute rounded border bg-white p-2 shadow"
            style={{
              left: (n.x ?? 0) + "px",
              top: (n.y ?? 0) + "px",
              width: NODE_W + "px",
              height: NODE_H + "px",
            }}
          >
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium" data-testid="node-label">{n.label}</span>
              <button
                type="button"
                data-testid={`remove-${n.id}`}
                onClick={() => removeNode(n.id)}
                aria-label="Remove node"
                className="text-xs text-red-500 hover:text-red-700"
              >
                ×
              </button>
            </div>
            <div className="text-xs text-gray-500">{n.kind}</div>
          </div>
        ))}
        {nodes.length === 0 && (
          <div
            data-testid="canvas-empty"
            className="absolute inset-0 flex items-center justify-center text-sm text-gray-500"
          >
            Click a node above to add it
          </div>
        )}
      </div>
    </div>
  );
}
