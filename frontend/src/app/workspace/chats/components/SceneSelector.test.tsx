import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SceneSelector } from "./SceneSelector";

describe("SceneSelector", () => {
  afterEach(() => cleanup());

  it("renders all five scenes", () => {
    render(<SceneSelector onChange={() => {}} />);
    expect(screen.getByText("Free Chat")).toBeInTheDocument();
    expect(screen.getByText("Knowledge Q&A")).toBeInTheDocument();
    expect(screen.getByText("Write Document")).toBeInTheDocument();
    expect(screen.getByText("Analyze Files")).toBeInTheDocument();
    expect(screen.getByText("Create Automation")).toBeInTheDocument();
  });

  it("calls onChange with the chosen scene", () => {
    const onChange = vi.fn();
    render(<SceneSelector onChange={onChange} />);
    fireEvent.click(screen.getByTestId("scene-qa"));
    expect(onChange).toHaveBeenCalledWith("qa");
  });

  it("marks selected scene with aria-checked", () => {
    render(<SceneSelector onChange={() => {}} />);
    expect(screen.getByTestId("scene-free").getAttribute("aria-checked")).toBe("true");
    fireEvent.click(screen.getByTestId("scene-automate"));
    expect(screen.getByTestId("scene-automate").getAttribute("aria-checked")).toBe("true");
    expect(screen.getByTestId("scene-free").getAttribute("aria-checked")).toBe("false");
  });

  it("renders as a radiogroup for accessibility", () => {
    render(<SceneSelector onChange={() => {}} />);
    expect(screen.getByRole("radiogroup")).toBeInTheDocument();
  });
});
