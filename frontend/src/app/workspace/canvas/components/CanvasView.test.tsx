import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CanvasView } from "./CanvasView";
import { NODE_KINDS } from "./types";

describe("CanvasView", () => {
  afterEach(() => cleanup());

  it("renders empty state with all 5 palette buttons", () => {
    render(<CanvasView />);
    expect(screen.getByTestId("canvas-empty")).toBeInTheDocument();
    for (const k of NODE_KINDS) {
      expect(screen.getByTestId(`palette-${k.value}`)).toBeInTheDocument();
    }
  });

  it("adds a node when a palette button is clicked", () => {
    render(<CanvasView />);
    fireEvent.click(screen.getByTestId("palette-agent"));
    const nodes = screen.getAllByTestId(/^node-n-/);
    expect(nodes).toHaveLength(1);
    const [node] = nodes;
    expect(node).toHaveAttribute("data-node-kind", "agent");
  });

  it("removes a node when × is clicked", () => {
    render(<CanvasView />);
    fireEvent.click(screen.getByTestId("palette-tool"));
    fireEvent.click(screen.getByTestId("palette-prompt"));
    expect(screen.getAllByTestId(/^node-n-/)).toHaveLength(2);
    const first = screen.getAllByTestId(/^node-n-/)[0];
    if (!first) throw new Error("expected at least one node");
    const removeBtn = within(first).getByRole("button", { name: /remove/i });
    fireEvent.click(removeBtn);
    expect(screen.getAllByTestId(/^node-n-/)).toHaveLength(1);
  });

  it("emits onChange when nodes change", () => {
    const onChange = vi.fn();
    render(<CanvasView onChange={onChange} />);
    fireEvent.click(screen.getByTestId("palette-branch"));
    expect(onChange).toHaveBeenCalledTimes(1);
    const [canvas] = onChange.mock.calls[0] as [{ nodes: unknown[] }];
    expect(canvas.nodes).toHaveLength(1);
  });

  it("labels nodes with kind + index", () => {
    render(<CanvasView />);
    fireEvent.click(screen.getByTestId("palette-loop"));
    fireEvent.click(screen.getByTestId("palette-loop"));
    const labels = screen.getAllByTestId("node-label");
    expect(labels[0]).toHaveTextContent("loop-1");
    expect(labels[1]).toHaveTextContent("loop-2");
  });

  it("uses initial nodes when provided", () => {
    const initial = {
      id: "c-1",
      name: "Test",
      nodes: [
        { id: "n-1", kind: "agent" as const, label: "starter" },
        { id: "n-2", kind: "tool" as const, label: "lookup" },
      ],
      edges: [],
    };
    render(<CanvasView initial={initial} />);
    expect(screen.getByTestId("node-n-1")).toBeInTheDocument();
    expect(screen.getByTestId("node-n-2")).toBeInTheDocument();
    expect(screen.queryByTestId("canvas-empty")).not.toBeInTheDocument();
  });
});
