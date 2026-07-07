import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkflowVersions } from "../hooks/use-workflow-versions";

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

describe("useWorkflowVersions", () => {
  it("does not fetch when workflowId is null", async () => {
    const { result } = renderHook(() => useWorkflowVersions(null));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("fetches and stores versions", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        versions: [
          { workflow_id: "w1", version: 1, created_at: "2026-07-01T00:00:00Z", snapshot: {} },
          { workflow_id: "w1", version: 2, created_at: "2026-07-02T00:00:00Z", snapshot: {} },
        ],
      }),
    );

    const { result } = renderHook(() => useWorkflowVersions("w1"));

    await waitFor(() => expect(result.current.versions).toHaveLength(2));
    expect(result.current.versions.map((v) => v.version)).toEqual([1, 2]);
  });

  it("rollback() re-fetches versions", async () => {
    mockFetch
      .mockResolvedValueOnce(
        jsonResponse({
          versions: [
            { workflow_id: "w1", version: 1, created_at: "t1", snapshot: {} },
            { workflow_id: "w1", version: 2, created_at: "t2", snapshot: {} },
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ id: "w1", version: 3 }))
      .mockResolvedValueOnce(
        jsonResponse({
          versions: [
            { workflow_id: "w1", version: 1, created_at: "t1", snapshot: {} },
            { workflow_id: "w1", version: 2, created_at: "t2", snapshot: {} },
            { workflow_id: "w1", version: 3, created_at: "t3", snapshot: {} },
          ],
        }),
      );

    const { result } = renderHook(() => useWorkflowVersions("w1"));
    await waitFor(() => expect(result.current.versions).toHaveLength(2));

    await act(async () => {
      await result.current.rollback(2);
    });

    await waitFor(() => expect(result.current.versions).toHaveLength(3));
  });
});
