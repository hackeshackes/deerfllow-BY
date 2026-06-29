import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import CanvasPage from "./page";

describe("CanvasPage", () => {
  afterEach(() => cleanup());

  it("renders the canvas shell with the 5 palette buttons", () => {
    render(<CanvasPage />);
    expect(screen.getByTestId("canvas-page")).toBeInTheDocument();
    for (const k of ["agent", "tool", "prompt", "branch", "loop"]) {
      expect(screen.getByTestId(`palette-${k}`)).toBeInTheDocument();
    }
  });

  it("shows empty state when no nodes are added", () => {
    render(<CanvasPage />);
    expect(screen.getByTestId("canvas-empty")).toBeInTheDocument();
  });
});
