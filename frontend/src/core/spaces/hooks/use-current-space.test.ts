import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

import { useCurrentSpace } from "./use-current-space";

describe("useCurrentSpace", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the current space and resolves", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ id: "personal", name: "Personal", type: "personal" })),
      ),
    );
    const { result } = renderHook(() => useCurrentSpace());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.space?.id).toBe("personal");
    expect(result.current.error).toBeNull();
  });

  it("captures errors in the result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("boom", { status: 500 })),
    );
    const { result } = renderHook(() => useCurrentSpace());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.space).toBeNull();
    expect(result.current.error).toMatch(/500/);
  });

  it("re-fetches when spaceId changes", async () => {
    const fetchMock = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      const id = (init?.headers as Record<string, string> | undefined)?.["X-MicX-Space"] ?? "personal";
      return new Response(JSON.stringify({ id, name: id, type: "workspace" }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { result, rerender } = renderHook(({ id }: { id?: string }) => useCurrentSpace(id), {
      initialProps: { id: "ws-1" as string | undefined },
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.space?.id).toBe("ws-1");

    rerender({ id: "ws-2" });
    await waitFor(() => expect(result.current.space?.id).toBe("ws-2"));
  });
});
