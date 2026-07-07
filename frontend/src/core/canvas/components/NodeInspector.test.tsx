import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CanvasEdge, CanvasNode } from "../types";

import { NodeInspector } from "./NodeInspector";

afterEach(() => cleanup());

const baseNode: CanvasNode = {
  id: "n1",
  kind: "prompt",
  config: {},
  position: [0, 0],
};

describe("NodeInspector", () => {
  it("renders empty placeholder when no node is selected", () => {
    render(<NodeInspector node={null} edges={[]} onUpdate={() => undefined} onRemove={() => undefined} />);
    const inspector = screen.getByTestId("node-inspector");
    expect(inspector.getAttribute("data-empty")).toBe("true");
    expect(inspector).toHaveTextContent(/Select a node/i);
  });

  it("renders the node id and kind for a PROMPT node", () => {
    render(
      <NodeInspector
        node={baseNode}
        edges={[]}
        onUpdate={() => undefined}
        onRemove={() => undefined}
      />,
    );
    const inspector = screen.getByTestId("node-inspector");
    expect(inspector.getAttribute("data-node-id")).toBe("n1");
    expect(inspector).toHaveTextContent("Prompt");
  });

  it("calls onRemove when Delete is clicked", () => {
    const onRemove = vi.fn();
    render(
      <NodeInspector
        node={baseNode}
        edges={[]}
        onUpdate={() => undefined}
        onRemove={onRemove}
      />,
    );
    fireEvent.click(screen.getByTestId("inspector-remove"));
    expect(onRemove).toHaveBeenCalledWith("n1");
  });

  it("renders template textarea for a PROMPT node and updates on change", () => {
    const onUpdate = vi.fn();
    render(
      <NodeInspector
        node={baseNode}
        edges={[]}
        onUpdate={onUpdate}
        onRemove={() => undefined}
      />,
    );
    const ta = screen.getByTestId("inspector-template");
    fireEvent.change(ta, { target: { value: "hello {{name}}" } });
    expect(onUpdate).toHaveBeenCalledWith("n1", {
      config: { template: "hello {{name}}" },
    });
  });

  it("renders iterations input for a LOOP node and clamps to int", () => {
    const loopNode: CanvasNode = { id: "l1", kind: "loop", config: { iterations: 3 }, position: [0, 0] };
    const onUpdate = vi.fn();
    render(
      <NodeInspector
        node={loopNode}
        edges={[]}
        onUpdate={onUpdate}
        onRemove={() => undefined}
      />,
    );
    const input = screen.getByTestId<HTMLInputElement>("inspector-iterations");
    expect(input.value).toBe("3");
    fireEvent.change(input, { target: { value: "7" } });
    expect(onUpdate).toHaveBeenCalledWith("l1", { config: { iterations: 7 } });
  });

  it("renders condition input for a BRANCH node", () => {
    const branchNode: CanvasNode = {
      id: "b1",
      kind: "branch",
      config: { condition: "score > 10" },
      position: [0, 0],
    };
    const onUpdate = vi.fn();
    render(
      <NodeInspector
        node={branchNode}
        edges={[]}
        onUpdate={onUpdate}
        onRemove={() => undefined}
      />,
    );
    const input = screen.getByTestId<HTMLInputElement>("inspector-condition");
    expect(input.value).toBe("score > 10");
  });

  it("lists connected edges", () => {
    const edges: CanvasEdge[] = [
      { id: "e1", source_node_id: "n1", target_node_id: "n2", condition: null },
      { id: "e2", source_node_id: "n3", target_node_id: "n1", condition: "true" },
    ];
    render(
      <NodeInspector
        node={baseNode}
        edges={edges}
        onUpdate={() => undefined}
        onRemove={() => undefined}
      />,
    );
    const listed = screen.getAllByTestId("inspector-edge");
    expect(listed).toHaveLength(2);
  });
});
