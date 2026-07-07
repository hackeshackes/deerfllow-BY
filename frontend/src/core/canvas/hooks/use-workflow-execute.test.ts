import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkflowExecute } from "../hooks/use-workflow-execute";

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

describe("useWorkflowExecute", () => {
  it("starts idle with no result/error", () => {
    const { result } = renderHook(() => useWorkflowExecute());
    expect(result.current.isRunning).toBe(false);
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("run() sets result on success", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        workflow_id: "w1",
        workflow_version: 1,
        outputs: { a: { text: "hi" } },
        steps: [],
        total_tokens: 0,
        failed_node_id: null,
      }),
    );

    const { result } = renderHook(() => useWorkflowExecute());

    await act(async () => {
      await result.current.run("w1", { inputs: {}, workspace_id: "ws-1" });
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.result?.outputs.a?.text).toBe("hi");
    expect(result.current.error).toBeNull();
  });

  it("run() surfaces error on 429 quota exceeded", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ error: { code: "QUOTA_EXCEEDED" } }, 429),
    );

    const { result } = renderHook(() => useWorkflowExecute());

    await act(async () => {
      await result.current.run("w1", { inputs: {}, workspace_id: "ws-1" });
    });

    expect(result.current.result).toBeNull();
    expect(result.current.error?.message).toMatch(/429/);
  });

  it("reset() clears result and error", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ error: { code: "QUOTA_EXCEEDED" } }, 429),
    );

    const { result } = renderHook(() => useWorkflowExecute());
    await act(async () => {
      await result.current.run("w1", { inputs: {}, workspace_id: "ws-1" });
    });
    expect(result.current.error).not.toBeNull();

    act(() => {
      result.current.reset();
    });

    expect(result.current.error).toBeNull();
    expect(result.current.result).toBeNull();
  });

  it("flips isRunning true during the request and back to false after", async () => {
    let resolveFetch!: (r: Response) => void;
    mockFetch.mockReturnValueOnce(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      }),
    );

    const { result } = renderHook(() => useWorkflowExecute());

    act(() => {
      void result.current.run("w1", { inputs: {}, workspace_id: "ws-1" });
    });

    await waitFor(() => expect(result.current.isRunning).toBe(true));

    await act(async () => {
      resolveFetch(
        jsonResponse({
          workflow_id: "w1",
          workflow_version: 1,
          outputs: {},
          steps: [],
          total_tokens: 0,
          failed_node_id: null,
        }),
      );
    });

    expect(result.current.isRunning).toBe(false);
  });
});
