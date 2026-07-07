"use client";

import type { NodeKind } from "../types";
import { NODE_KINDS } from "../types";

/**
 * Node palette — click a button to add a new node of that kind.
 * Lives outside the React Flow surface so the toolbar is always
 * reachable even when zoomed/panned.
 *
 * Contract:
 *   - data-testid="palette-{kind}" per kind button
 *   - data-testid="node-palette" on the container
 */
interface NodePaletteProps {
  onAdd: (kind: NodeKind) => void;
  disabled?: boolean;
}

export function NodePalette({ onAdd, disabled = false }: NodePaletteProps) {
  return (
    <div
      className="flex flex-wrap gap-2 border-b p-2"
      role="toolbar"
      aria-label="Node palette"
      data-testid="node-palette"
    >
      {NODE_KINDS.map((k) => (
        <button
          key={k.value}
          type="button"
          data-testid={`palette-${k.value}`}
          aria-label={`Add ${k.label} node`}
          title={k.description}
          disabled={disabled}
          onClick={() => onAdd(k.value)}
          className="rounded border px-3 py-1 text-sm hover:bg-gray-50 disabled:opacity-50"
        >
          + {k.label}
        </button>
      ))}
    </div>
  );
}
