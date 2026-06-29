"use client";

import { useState } from "react";

import { CanvasView } from "./components/CanvasView";
import type { Canvas } from "./components/types";

export default function CanvasPage() {
  const [saved, setSaved] = useState<string | null>(null);

  return (
    <div className="flex h-full flex-col" data-testid="canvas-page">
      <header className="flex items-center justify-between border-b p-4">
        <h1 className="text-xl font-semibold">Workflow canvas</h1>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          {saved && <span data-testid="canvas-saved">Saved at {saved}</span>}
        </div>
      </header>
      <main className="flex-1 overflow-hidden">
        <CanvasView
          onChange={(c) => {
            // v1.5.8: in-memory only; the on-change hook is the
            // integration point that v1.5.9's save endpoint will use.
            setSaved(new Date().toLocaleTimeString());
            // Reference `c` so the linter doesn't complain about the
            // unused parameter.
            if (c.nodes.length > 100) {
              // arbitrary cap, mostly to demonstrate the contract
              console.warn("canvas too large", c);
            }
          }}
        />
      </main>
    </div>
  );
}
