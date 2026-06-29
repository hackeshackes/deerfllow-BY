import { describe, it, expect, vi, beforeEach } from "vitest";

import { spacesApi } from "./api";

describe("spacesApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("list fetches /api/spaces and parses the envelope", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({ spaces: [{ id: "personal", name: "Personal", type: "personal" }] }),
      ),
    );
    const { spaces } = await spacesApi.list();
    expect(spaces[0]?.id).toBe("personal");
  });

  it("current sends X-MicX-Space header when spaceId provided", async () => {
    const captured: { url?: string; headers?: Record<string, string> } = {};
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      captured.url = String(url);
      captured.headers = (init?.headers as Record<string, string>) || {};
      return new Response(JSON.stringify({ id: "ws-1", name: "X", type: "workspace" }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const space = await spacesApi.current("ws-1");
    expect(space.id).toBe("ws-1");
    expect(captured.headers?.["X-MicX-Space"]).toBe("ws-1");
  });

  it("current omits header when spaceId is undefined", async () => {
    const captured: { headers?: Record<string, string> } = {};
    const fetchMock = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      captured.headers = (init?.headers as Record<string, string>) || {};
      return new Response(JSON.stringify({ id: "personal", name: "Personal", type: "personal" }));
    });
    vi.stubGlobal("fetch", fetchMock);
    await spacesApi.current();
    expect(captured.headers?.["X-MicX-Space"]).toBeUndefined();
  });

  it("get encodes the spaceId in the URL", async () => {
    let capturedUrl = "";
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      capturedUrl = String(url);
      return new Response(JSON.stringify({ id: "ws product", name: "WS", type: "workspace" }));
    });
    vi.stubGlobal("fetch", fetchMock);
    await spacesApi.get("ws product");
    expect(capturedUrl).toContain("/api/spaces/ws%20product");
  });

  it("throws on non-2xx response with the status code", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("not found", { status: 404 })),
    );
    await expect(spacesApi.list()).rejects.toThrow(/404/);
  });
});
