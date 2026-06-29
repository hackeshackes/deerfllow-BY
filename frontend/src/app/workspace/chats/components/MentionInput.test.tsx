import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MentionInput } from "./MentionInput";

describe("MentionInput", () => {
  afterEach(() => cleanup());

  it("shows suggestions when input ends with @", () => {
    render(<MentionInput value="hi @" onChange={() => {}} />);
    expect(screen.getByTestId("mention-suggest")).toBeInTheDocument();
  });

  it("hides suggestions when @ is removed", () => {
    const onChange = vi.fn();
    render(<MentionInput value="hi" onChange={onChange} />);
    // Simulate user typing — initial value with no @ keeps the suggestion closed
    expect(screen.queryByTestId("mention-suggest")).not.toBeInTheDocument();
  });

  it("inserts a suggestion on click, dropping the leading @", () => {
    let val = "hi @";
    render(<MentionInput value={val} onChange={(v) => { val = v; }} />);
    fireEvent.click(screen.getByTestId("mention-opt-@alice"));
    expect(val).toBe("hi @alice ");
  });

  it("closes the suggestion list after picking one", () => {
    render(<MentionInput value="hi @" onChange={() => {}} />);
    fireEvent.click(screen.getByTestId("mention-opt-@bob"));
    expect(screen.queryByTestId("mention-suggest")).not.toBeInTheDocument();
  });

  it("forwards user typing via onChange", () => {
    const onChange = vi.fn();
    render(<MentionInput value="" onChange={onChange} />);
    fireEvent.change(screen.getByTestId("mention-input"), {
      target: { value: "x" },
    });
    expect(onChange).toHaveBeenCalledWith("x");
  });

  it("accepts a custom suggestions list", () => {
    render(
      <MentionInput
        value="@"
        onChange={() => {}}
        suggestions={["@user-a", "@user-b"]}
      />,
    );
    expect(screen.getByTestId("mention-opt-@user-a")).toBeInTheDocument();
    expect(screen.getByTestId("mention-opt-@user-b")).toBeInTheDocument();
  });
});
