"use client";

import { useMemo } from "react";

import type { CanvasEdge, CanvasNode } from "../types";
import { NODE_KINDS } from "../types";

interface NodeInspectorProps {
  node: CanvasNode | null;
  edges: CanvasEdge[];
  onUpdate: (id: string, patch: Partial<CanvasNode>) => void;
  onRemove: (id: string) => void;
}

/**
 * Inspector for a single canvas node. Edits config (template, condition,
 * iterations, prompt, tool_name + args) inline. Shows connected edges.
 */
export function NodeInspector({ node, edges, onUpdate, onRemove }: NodeInspectorProps) {
  const connected = useMemo(
    () => (node ? edges.filter((e) => e.source_node_id === node.id || e.target_node_id === node.id) : []),
    [node, edges],
  );

  if (!node) {
    return (
      <aside
        className="w-72 border-l p-4 text-sm text-gray-500"
        data-testid="node-inspector"
        data-empty="true"
        aria-label="Node inspector"
      >
        Select a node to inspect.
      </aside>
    );
  }

  const kind = node.kind;
  const kindLabel = NODE_KINDS.find((k) => k.value === kind)?.label ?? kind;

  return (
    <aside
      className="w-72 space-y-3 border-l p-4 text-sm"
      data-testid="node-inspector"
      data-node-id={node.id}
      aria-label={`Inspector for ${kindLabel} node`}
    >
      <header className="flex items-center justify-between">
        <div>
          <div className="font-medium">{kindLabel}</div>
          <div className="text-xs text-gray-500">{node.id}</div>
        </div>
        <button
          type="button"
          data-testid="inspector-remove"
          onClick={() => onRemove(node.id)}
          className="rounded border px-2 py-0.5 text-xs text-red-600 hover:bg-red-50"
        >
          Delete
        </button>
      </header>

      {kind === "prompt" && <PromptFields node={node} onUpdate={onUpdate} />}
      {kind === "agent" && <AgentFields node={node} onUpdate={onUpdate} />}
      {kind === "tool" && <ToolFields node={node} onUpdate={onUpdate} />}
      {kind === "branch" && <BranchFields node={node} onUpdate={onUpdate} />}
      {kind === "loop" && <LoopFields node={node} onUpdate={onUpdate} />}

      <section>
        <h4 className="mb-1 text-xs font-semibold uppercase text-gray-500">Connected edges</h4>
        {connected.length === 0 ? (
          <p className="text-xs text-gray-400">No edges yet.</p>
        ) : (
          <ul className="space-y-1 text-xs">
            {connected.map((e) => (
              <li
                key={e.id}
                data-testid="inspector-edge"
                className="rounded border bg-gray-50 px-2 py-1"
              >
                <code>{e.source_node_id}</code> → <code>{e.target_node_id}</code>
                {e.condition && (
                  <span className="ml-1 rounded bg-blue-50 px-1 text-blue-700">[{e.condition}]</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}

type FieldProps = { node: CanvasNode; onUpdate: (id: string, patch: Partial<CanvasNode>) => void };

function PromptFields({ node, onUpdate }: FieldProps) {
  return (
    <Field label="Template" hint="Use {{var}} placeholders.">
      <textarea
        data-testid="inspector-template"
        value={(node.config.template!) ?? ""}
        onChange={(e) => onUpdate(node.id, { config: { ...node.config, template: e.target.value } })}
        className="h-24 w-full rounded border p-2 font-mono text-xs"
      />
    </Field>
  );
}

function AgentFields({ node, onUpdate }: FieldProps) {
  return (
    <Field label="Agent prompt" hint="Sent to the LLM. {{var}} interpolation.">
      <textarea
        data-testid="inspector-prompt"
        value={(node.config.prompt!) ?? ""}
        onChange={(e) => onUpdate(node.id, { config: { ...node.config, prompt: e.target.value } })}
        className="h-24 w-full rounded border p-2 font-mono text-xs"
      />
    </Field>
  );
}

function ToolFields({ node, onUpdate }: FieldProps) {
  const toolName = (node.config.tool_name!) ?? "";
  const argsText = JSON.stringify(node.config.args ?? {}, null, 2);
  return (
    <>
      <Field label="Tool name">
        <input
          data-testid="inspector-tool-name"
          type="text"
          value={toolName}
          onChange={(e) => onUpdate(node.id, { config: { ...node.config, tool_name: e.target.value } })}
          className="w-full rounded border p-1 text-xs"
        />
      </Field>
      <Field label="Args (JSON object)" hint="Workflow inputs override these unless 'fixed'.">
        <textarea
          data-testid="inspector-tool-args"
          value={argsText}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value) as Record<string, unknown>;
              onUpdate(node.id, { config: { ...node.config, args: parsed } });
            } catch {
              // ignore mid-typing
            }
          }}
          className="h-24 w-full rounded border p-2 font-mono text-xs"
        />
      </Field>
    </>
  );
}

function BranchFields({ node, onUpdate }: FieldProps) {
  return (
    <Field label="Condition" hint="Example: score > 10  or  status in {active,pending}">
      <input
        data-testid="inspector-condition"
        type="text"
        value={(node.config.condition!) ?? ""}
        onChange={(e) => onUpdate(node.id, { config: { ...node.config, condition: e.target.value } })}
        className="w-full rounded border p-1 font-mono text-xs"
        placeholder="score > 10"
      />
    </Field>
  );
}

function LoopFields({ node, onUpdate }: FieldProps) {
  const raw = node.config.iterations;
  const value = typeof raw === "number" ? String(raw) : "";
  return (
    <Field label="Iterations" hint="Integer in [1, 1000].">
      <input
        data-testid="inspector-iterations"
        type="number"
        min={1}
        max={1000}
        value={value}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (Number.isFinite(n)) {
            onUpdate(node.id, { config: { ...node.config, iterations: n } });
          }
        }}
        className="w-full rounded border p-1 text-xs"
      />
    </Field>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase text-gray-500">{label}</span>
      {hint && <span className="block text-xs text-gray-400">{hint}</span>}
      <div className="mt-1">{children}</div>
    </label>
  );
}
