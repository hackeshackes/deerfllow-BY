import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { canvasApi } from "./api";

let mockFetch: ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockFetch = vi.fn();
  global.fetch = mockFetch as unknown as typeof fetch;
});

afterEach(() => {
  vi.restoreAllMocks();
});

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "ERR",
    json: async () => body,
  } as Response;
}

describe("canvasApi.list", () => {
  it("calls GET /api/workflows with workspace_id query", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ workflows: [] }));

    await canvasApi.list("ws-1");

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workflows?workspace_id=ws-1");
    expect(init.credentials).toBe("include");
    expect(init.method).toBeUndefined();
  });

  it("encodes special characters in workspace_id", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ workflows: [] }));

    await canvasApi.list("ws with space");

    const [url] = mockFetch.mock.calls[0] as [string];
    expect(url).toBe("/api/workflows?workspace_id=ws%20with%20space");
  });
});

describe("canvasApi.get", () => {
  it("calls GET /api/workflows/{id}", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "w1", name: "demo" }));

    await canvasApi.get("w1");

    const [url] = mockFetch.mock.calls[0] as [string];
    expect(url).toBe("/api/workflows/w1");
  });
});

describe("canvasApi.create", () => {
  it("POSTs JSON body to /api/workflows", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "w-new" }));

    await canvasApi.create({ name: "demo", workspace_id: "ws-1" });

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workflows");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ name: "demo", workspace_id: "ws-1" });
  });
});

describe("canvasApi.update", () => {
  it("PUTs partial body to /api/workflows/{id}", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "w1", version: 2 }));

    await canvasApi.update("w1", { name: "renamed" });

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workflows/w1");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({ name: "renamed" });
  });
});

describe("canvasApi.remove", () => {
  it("DELETEs /api/workflows/{id}", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ success: true }));

    await canvasApi.remove("w1");

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workflows/w1");
    expect(init.method).toBe("DELETE");
  });
});

describe("canvasApi.execute", () => {
  it("POSTs inputs + workspace_id to /api/workflows/{id}/execute", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        workflow_id: "w1",
        workflow_version: 1,
        outputs: {},
        steps: [],
        total_tokens: 0,
        failed_node_id: null,
      }),
    );

    await canvasApi.execute("w1", { inputs: { x: 1 }, workspace_id: "ws-1", estimated_tokens: 50 });

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workflows/w1/execute");
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body as string);
    expect(body).toEqual({ inputs: { x: 1 }, workspace_id: "ws-1", estimated_tokens: 50 });
  });
});

describe("canvasApi.rollback", () => {
  it("POSTs to /api/workflows/{id}/rollback/{version}", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "w1" }));

    await canvasApi.rollback("w1", 3);

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workflows/w1/rollback/3");
    expect(init.method).toBe("POST");
  });
});

describe("canvasApi error handling", () => {
  it("throws Error with status + parsed body when response is not ok", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "QUOTA_EXCEEDED" }, 429),
    );

    await expect(canvasApi.list("ws-1")).rejects.toThrow(/429/);
  });
});
