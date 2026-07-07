import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CanvasNode } from "../types";

import { EdgeConnector } from "./EdgeConnector";

afterEach(() => cleanup());

const aNode: CanvasNode = { id: "n-a", kind: "prompt", config: {}, position: [0, 0] };
const bNode: CanvasNode = { id: "n-b", kind: "tool", config: {}, position: [10, 10] };

describe("EdgeConnector", () => {
  it("shows a disabled hint when fewer than 2 nodes exist", () => {
    render(<EdgeConnector nodes={[aNode]} onCreate={() => undefined} />);
    const root = screen.getByTestId("edge-connector");
    expect(root.getAttribute("data-disabled-reason")).toBe("need-2-nodes");
  });

  it("opens the form when the trigger is clicked", () => {
    render(<EdgeConnector nodes={[aNode, bNode]} onCreate={() => undefined} />);
    fireEvent.click(screen.getByTestId("edge-connector-trigger"));
    expect(screen.getByTestId("edge-connector-form")).toBeInTheDocument();
  });

  it("submits an edge with null condition by default", () => {
    const onCreate = vi.fn();
    render(<EdgeConnector nodes={[aNode, bNode]} onCreate={onCreate} />);
    fireEvent.click(screen.getByTestId("edge-connector-trigger"));
    fireEvent.change(screen.getByTestId("edge-connector-source"), { target: { value: "n-a" } });
    fireEvent.change(screen.getByTestId("edge-connector-target"), { target: { value: "n-b" } });
    fireEvent.click(screen.getByTestId("edge-connector-submit"));
    expect(onCreate).toHaveBeenCalledWith({
      source_node_id: "n-a",
      target_node_id: "n-b",
      condition: null,
    });
  });

  it("includes condition label when branch-condition toggle is on", () => {
    const onCreate = vi.fn();
    render(<EdgeConnector nodes={[aNode, bNode]} onCreate={onCreate} />);
    fireEvent.click(screen.getByTestId("edge-connector-trigger"));
    fireEvent.change(screen.getByTestId("edge-connector-source"), { target: { value: "n-a" } });
    fireEvent.change(screen.getByTestId("edge-connector-target"), { target: { value: "n-b" } });
    fireEvent.click(screen.getByTestId("edge-connector-condition-toggle"));
    fireEvent.change(screen.getByTestId("edge-connector-condition"), { target: { value: "false" } });
    fireEvent.click(screen.getByTestId("edge-connector-submit"));
    expect(onCreate).toHaveBeenCalledWith({
      source_node_id: "n-a",
      target_node_id: "n-b",
      condition: "false",
    });
  });

  it("does not submit when source equals target", () => {
    const onCreate = vi.fn();
    render(<EdgeConnector nodes={[aNode, bNode]} onCreate={onCreate} />);
    fireEvent.click(screen.getByTestId("edge-connector-trigger"));
    fireEvent.change(screen.getByTestId("edge-connector-source"), { target: { value: "n-a" } });
    fireEvent.change(screen.getByTestId("edge-connector-target"), { target: { value: "n-a" } });
    expect(screen.getByTestId("edge-connector-submit")).toBeDisabled();
  });
});
