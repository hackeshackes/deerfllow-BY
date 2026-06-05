import { describe, it, expect } from "vitest";

import { tryParseJSON } from "./json";

describe("tryParseJSON", () => {
  it("parses well-formed JSON into the corresponding value", () => {
    expect(tryParseJSON('{"a":1,"b":"two"}')).toEqual({ a: 1, b: "two" });
  });

  it("parses JSON arrays", () => {
    expect(tryParseJSON("[1, 2, 3]")).toEqual([1, 2, 3]);
  });

  it("parses best-effort JSON (trailing comma, unquoted keys)", () => {
    // best-effort-json-parser is more lenient than JSON.parse
    const result = tryParseJSON('{a: 1, b: 2,}');
    expect(result).toEqual({ a: 1, b: 2 });
  });

  it("returns undefined when the input is not parseable", () => {
    expect(tryParseJSON("{ broken: , }")).toBeUndefined();
  });

  it("returns a falsy value (empty string) for an empty input", () => {
    // best-effort-json-parser does not throw on empty input — it returns "".
    // We only assert that it does not throw and that callers can safely check.
    expect(tryParseJSON("")).toBeFalsy();
  });
});
