import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { loadKnowledgeBases } from "./api";

const originalFetch = globalThis.fetch;

describe("loadKnowledgeBases", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns the parsed array on a 2xx response", async () => {
    const kbs = [{ id: "kb-1" }, { id: "kb-2" }];
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(kbs), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ) as unknown as typeof fetch;

    const result = await loadKnowledgeBases();
    expect(result).toEqual(kbs);
  });

  // Regression: P0-2 — when /api/session/me or any other auth-checked
  // dependency returns 401, the store used to receive the error envelope
  // and a downstream `n.filter is not a function` would crash the page.
  it("returns an empty array on a 401 response so consumers never call .filter on undefined", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not authenticated" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    ) as unknown as typeof fetch;

    const result = await loadKnowledgeBases();
    expect(result).toEqual([]);
    // Smoke-check the consumer contract: a downstream filter must not throw.
    expect(() => result.filter((kb) => kb.id === "kb-1")).not.toThrow();
  });

  it("returns an empty array when the response body is not an array", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Server error" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ) as unknown as typeof fetch;

    const result = await loadKnowledgeBases();
    expect(result).toEqual([]);
  });
});
