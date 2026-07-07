import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CanvasEdge, CanvasNode } from "../types";

import { Canvas } from "./Canvas";

afterEach(() => cleanup());

const sampleNodes: CanvasNode[] = [
  { id: "a", kind: "prompt", config: {}, position: [40, 40] },
  { id: "b", kind: "tool", config: {}, position: [240, 40] },
];

const sampleEdges: CanvasEdge[] = [
  { id: "e1", source_node_id: "a", target_node_id: "b", condition: null },
];

describe("Canvas", () => {
  it("renders the empty placeholder when no nodes", () => {
    render(
      <Canvas
        nodes={[]}
        edges={[]}
        onNodesChange={() => undefined}
        onEdgesChange={() => undefined}
        onSelectNode={() => undefined}
        selectedNodeId={null}
      />,
    );
    expect(screen.getByTestId("canvas-empty")).toBeInTheDocument();
  });

  it("renders a tile per node", () => {
    render(
      <Canvas
        nodes={sampleNodes}
        edges={sampleEdges}
        onNodesChange={() => undefined}
        onEdgesChange={() => undefined}
        onSelectNode={() => undefined}
        selectedNodeId={null}
      />,
    );
    expect(screen.getByTestId("node-a")).toBeInTheDocument();
    expect(screen.getByTestId("node-b")).toBeInTheDocument();
    expect(screen.getAllByTestId("node-label")).toHaveLength(2);
  });

  it("marks the selected node with data-selected=true", () => {
    render(
      <Canvas
        nodes={sampleNodes}
        edges={sampleEdges}
        onNodesChange={() => undefined}
        onEdgesChange={() => undefined}
        onSelectNode={() => undefined}
        selectedNodeId="a"
      />,
    );
    expect(screen.getByTestId("node-a").getAttribute("data-selected")).toBe("true");
    expect(screen.getByTestId("node-b").getAttribute("data-selected")).toBe("false");
  });

  it("calls onSelectNode when a node tile is clicked", () => {
    const onSelectNode = vi.fn();
    render(
      <Canvas
        nodes={sampleNodes}
        edges={sampleEdges}
        onNodesChange={() => undefined}
        onEdgesChange={() => undefined}
        onSelectNode={onSelectNode}
        selectedNodeId={null}
      />,
    );
    fireEvent.click(screen.getByTestId("node-a"));
    expect(onSelectNode).toHaveBeenCalledWith("a");
  });

  it("removes the node and incident edges when × is clicked", () => {
    const onNodesChange = vi.fn();
    const onEdgesChange = vi.fn();
    render(
      <Canvas
        nodes={sampleNodes}
        edges={sampleEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onSelectNode={() => undefined}
        selectedNodeId={null}
      />,
    );
    fireEvent.click(screen.getByTestId("node-remove-a"));
    expect(onNodesChange).toHaveBeenCalledWith([sampleNodes[1]]);
    expect(onEdgesChange).toHaveBeenCalledWith([]);
  });
});
