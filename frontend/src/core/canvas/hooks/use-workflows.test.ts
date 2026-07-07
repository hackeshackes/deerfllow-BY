import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkflows } from "../hooks/use-workflows";

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
    statusText: "OK",
    json: async () => body,
  } as Response;
}

describe("useWorkflows", () => {
  it("does not fetch when workspaceId is null", async () => {
    const { result } = renderHook(() => useWorkflows(null));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(mockFetch).not.toHaveBeenCalled();
    expect(result.current.workflows).toEqual([]);
  });

  it("fetches and stores workflows for a workspace", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        workflows: [
          { id: "w1", name: "demo", version: 1, status: "draft", nodes: [], edges: [] },
        ],
      }),
    );

    const { result } = renderHook(() => useWorkflows("ws-1"));

    await waitFor(() => expect(result.current.workflows).toHaveLength(1));
    expect(result.current.workflows[0]?.id).toBe("w1");
    expect(result.current.error).toBeNull();
  });

  it("captures error when fetch fails", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "nope" }, 500));

    const { result } = renderHook(() => useWorkflows("ws-1"));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error?.message).toMatch(/500/);
    expect(result.current.workflows).toEqual([]);
  });

  it("create() optimistically appends the new workflow", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({ workflows: [] }))
      .mockResolvedValueOnce(
        jsonResponse({ id: "w-new", name: "fresh", version: 1, status: "draft", nodes: [], edges: [] }),
      );

    const { result } = renderHook(() => useWorkflows("ws-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.create({ name: "fresh", workspace_id: "ws-1" });
    });

    expect(result.current.workflows).toHaveLength(1);
    expect(result.current.workflows[0]?.id).toBe("w-new");
  });

  it("remove() filters the workflow out of the list", async () => {
    mockFetch
      .mockResolvedValueOnce(
        jsonResponse({
          workflows: [
            { id: "w1", name: "a", version: 1, status: "draft", nodes: [], edges: [] },
            { id: "w2", name: "b", version: 1, status: "draft", nodes: [], edges: [] },
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ success: true }));

    const { result } = renderHook(() => useWorkflows("ws-1"));
    await waitFor(() => expect(result.current.workflows).toHaveLength(2));

    await act(async () => {
      await result.current.remove("w1");
    });

    expect(result.current.workflows.map((w) => w.id)).toEqual(["w2"]);
  });
});
