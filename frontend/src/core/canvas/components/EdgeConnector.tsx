"use client";

import { useState } from "react";

import type { CanvasEdge, CanvasNode } from "../types";

/**
 * Edge connector — two-step helper for creating a new edge between two
 * existing nodes. Optionally tags the edge with a routing condition
 * ("true" / "false") for BRANCH nodes.
 *
 * Contract:
 *   - data-testid="edge-connector-trigger" opens the form
 *   - data-testid="edge-connector-form"  the form root
 *   - data-testid="edge-connector-source" / "-target" selects
 *   - data-testid="edge-connector-condition" checkbox toggle + select
 *   - data-testid="edge-connector-submit"   creates the edge via onCreate
 */
interface EdgeConnectorProps {
  nodes: CanvasNode[];
  onCreate: (edge: Omit<CanvasEdge, "id">) => void;
}

export function EdgeConnector({ nodes, onCreate }: EdgeConnectorProps) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<string>("");
  const [target, setTarget] = useState<string>("");
  const [useCondition, setUseCondition] = useState(false);
  const [condition, setCondition] = useState<"true" | "false">("true");

  const canSubmit = source !== "" && target !== "" && source !== target;

  const reset = () => {
    setSource("");
    setTarget("");
    setUseCondition(false);
    setCondition("true");
  };

  const submit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!canSubmit) return;
    onCreate({
      source_node_id: source,
      target_node_id: target,
      condition: useCondition ? condition : null,
    });
    reset();
    setOpen(false);
  };

  if (nodes.length < 2) {
    return (
      <div
        className="border-b p-2 text-xs text-gray-500"
        data-testid="edge-connector"
        data-disabled-reason="need-2-nodes"
      >
        Add at least 2 nodes to connect them.
      </div>
    );
  }

  return (
    <div className="border-b p-2" data-testid="edge-connector">
      {!open && (
        <button
          type="button"
          data-testid="edge-connector-trigger"
          onClick={() => setOpen(true)}
          className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
        >
          + Connect nodes
        </button>
      )}
      {open && (
        <form
          data-testid="edge-connector-form"
          onSubmit={submit}
          className="flex flex-wrap items-end gap-2"
        >
          <label className="text-xs">
            <span className="block font-semibold uppercase text-gray-500">From</span>
            <select
              data-testid="edge-connector-source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="rounded border p-1 text-xs"
            >
              <option value="">—</option>
              {nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.id} ({n.kind})
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs">
            <span className="block font-semibold uppercase text-gray-500">To</span>
            <select
              data-testid="edge-connector-target"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="rounded border p-1 text-xs"
            >
              <option value="">—</option>
              {nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.id} ({n.kind})
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-1 text-xs">
            <input
              data-testid="edge-connector-condition-toggle"
              type="checkbox"
              checked={useCondition}
              onChange={(e) => setUseCondition(e.target.checked)}
            />
            branch condition
          </label>
          {useCondition && (
            <select
              data-testid="edge-connector-condition"
              value={condition}
              onChange={(e) => setCondition(e.target.value as "true" | "false")}
              className="rounded border p-1 text-xs"
            >
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          )}
          <button
            type="submit"
            data-testid="edge-connector-submit"
            disabled={!canSubmit}
            className="rounded bg-blue-600 px-3 py-1 text-xs text-white disabled:opacity-50"
          >
            Connect
          </button>
          <button
            type="button"
            onClick={() => {
              reset();
              setOpen(false);
            }}
            className="rounded border px-3 py-1 text-xs"
          >
            Cancel
          </button>
        </form>
      )}
    </div>
  );
}
