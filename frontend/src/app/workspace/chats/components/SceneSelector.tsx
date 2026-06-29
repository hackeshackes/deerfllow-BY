"use client";

import { useState } from "react";

export type ChatScene = "free" | "qa" | "document" | "analyze" | "automate";

interface SceneOption {
  value: ChatScene;
  label: string;
  description: string;
}

const SCENES: ReadonlyArray<SceneOption> = [
  { value: "free", label: "Free Chat", description: "Open conversation" },
  { value: "qa", label: "Knowledge Q&A", description: "Ask questions against selected knowledge bases" },
  { value: "document", label: "Write Document", description: "Generate a document from prompt" },
  { value: "analyze", label: "Analyze Files", description: "Analyze uploaded files" },
  { value: "automate", label: "Create Automation", description: "Convert this into a scheduled task" },
];

/**
 * Scene selector for new-chat flow. Reports the chosen scene via `onChange`.
 * The component owns its own selection state but defers to the parent for
 * how to use it (e.g. pre-filling a system prompt, redirecting).
 */
export function SceneSelector({ onChange }: { onChange: (scene: ChatScene) => void }) {
  const [selected, setSelected] = useState<ChatScene>("free");

  return (
    <div
      data-testid="scene-selector"
      className="grid grid-cols-2 gap-2 md:grid-cols-3"
      role="radiogroup"
      aria-label="New chat scene"
    >
      {SCENES.map((s) => (
        <button
          key={s.value}
          type="button"
          role="radio"
          aria-checked={selected === s.value}
          data-testid={`scene-${s.value}`}
          className={`rounded border p-3 text-left ${
            selected === s.value ? "border-blue-500 bg-blue-50" : ""
          }`}
          onClick={() => {
            setSelected(s.value);
            onChange(s.value);
          }}
        >
          <div className="font-medium">{s.label}</div>
          <div className="text-xs text-gray-500">{s.description}</div>
        </button>
      ))}
    </div>
  );
}
