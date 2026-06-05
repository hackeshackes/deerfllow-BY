import { describe, it, expect } from "vitest";

import { extractTitleFromMarkdown } from "./markdown";

describe("extractTitleFromMarkdown", () => {
  it("returns the title when the markdown starts with a single H1 heading", () => {
    expect(extractTitleFromMarkdown("# Hello World\n\nbody")).toBe("Hello World");
  });

  it("trims leading and trailing whitespace around the title", () => {
    expect(extractTitleFromMarkdown("#    Spaced Out    \nrest")).toBe("Spaced Out");
  });

  it("returns undefined when the markdown does not start with an H1", () => {
    expect(extractTitleFromMarkdown("## Subheading\n\nbody")).toBeUndefined();
  });

  it("returns undefined for plain text without any heading marker", () => {
    expect(extractTitleFromMarkdown("just some text\nmore text")).toBeUndefined();
  });
});
