import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NODE_KINDS } from "../types";

import { NodePalette } from "./NodePalette";

describe("NodePalette", () => {
  afterEach(() => cleanup());

  it("renders one button per node kind", () => {
    render(<NodePalette onAdd={() => undefined} />);
    for (const k of NODE_KINDS) {
      expect(screen.getByTestId(`palette-${k.value}`)).toBeInTheDocument();
    }
  });

  it("calls onAdd with the kind when a button is clicked", () => {
    const onAdd = vi.fn();
    render(<NodePalette onAdd={onAdd} />);
    fireEvent.click(screen.getByTestId("palette-prompt"));
    fireEvent.click(screen.getByTestId("palette-branch"));
    expect(onAdd).toHaveBeenCalledTimes(2);
    expect(onAdd).toHaveBeenNthCalledWith(1, "prompt");
    expect(onAdd).toHaveBeenNthCalledWith(2, "branch");
  });

  it("disables all buttons when disabled=true", () => {
    render(<NodePalette onAdd={() => undefined} disabled />);
    for (const k of NODE_KINDS) {
      expect(screen.getByTestId(`palette-${k.value}`)).toBeDisabled();
    }
  });
});
