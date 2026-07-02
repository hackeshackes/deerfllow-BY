import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CostPage from "../page";

type FetchFn = typeof fetch;
type MockedFetch = ReturnType<typeof vi.fn>;

let mockFetch: MockedFetch;
beforeEach(() => {
  mockFetch = vi.fn();
  global.fetch = mockFetch as unknown as FetchFn;
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const usageSummary = {
  tenant_id: "default",
  total_tokens: 12_345,
  total_requests: 42,
  by_tenant: [{ entity_id: "default", total_tokens: 12_345, request_count: 42 }],
  by_user: [{ entity_id: "alice", total_tokens: 8_000, request_count: 30 }],
  by_model: [
    { entity_id: "gpt-4", total_tokens: 8_000, request_count: 30 },
    { entity_id: "claude-3", total_tokens: 4_345, request_count: 12 },
  ],
};

const quota = {
  tenant_id: "default",
  max_tokens: 100_000,
  max_rpm: 60,
  period: "monthly" as const,
  enforce_mode: "advisory" as const,
};

describe("CostPage", () => {
  it("renders the empty state when no usage is recorded", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        tenant_id: "default",
        total_tokens: 0,
        total_requests: 0,
        by_tenant: [],
        by_user: [],
        by_model: [],
      }),
    } as Response);

    render(<CostPage />);

    expect(await screen.findByTestId("cost-dashboard")).toBeInTheDocument();
    expect(await screen.findByText(/No usage recorded yet/i)).toBeInTheDocument();
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/admin/cost/summary?tenant_id=default");
    expect(init.credentials).toBe("include");
  });

  it("renders usage data when the summary fetch succeeds", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => usageSummary,
    } as Response);

    render(<CostPage />);

    await waitFor(() => screen.getByTestId("cost-summary"));
    expect(screen.getByText(/12,345 tokens/)).toBeInTheDocument();
    expect(screen.getByTestId("cost-row-gpt-4")).toBeInTheDocument();
    expect(screen.getByTestId("cost-row-claude-3")).toBeInTheDocument();
    expect(screen.getByText(/42 requests · tenant default/i)).toBeInTheDocument();
  });

  it("saveQuota triggers a PUT to /api/admin/quota/{tenant_id}", async () => {
    mockFetch
      // initial cost/summary GET on mount
      .mockResolvedValueOnce({
        ok: true,
        json: async () => usageSummary,
      } as Response)
      // Reload quota GET
      .mockResolvedValueOnce({
        ok: true,
        json: async () => quota,
      } as Response)
      // Save quota PUT
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...quota, enforce_mode: "hard" }),
      } as Response);

    render(<CostPage />);

    // Wait for initial summary fetch to settle so quota reload doesn't race.
    await waitFor(() => screen.getByTestId("cost-summary"));

    // Reload the quota first so internal `quota` state has values to send.
    fireEvent.click(screen.getByTestId("cost-quota-reload"));
    await waitFor(() => screen.getByTestId("cost-quota"));

    // Switch enforce mode to "hard"
    const select = screen.getByTestId<HTMLSelectElement>("cost-enforce-mode");
    fireEvent.change(select, { target: { value: "hard" } });

    // Save
    fireEvent.click(screen.getByTestId("cost-quota-save"));

    await waitFor(() => {
      const putCall = mockFetch.mock.calls.find((call) => {
        const init = call[1] as RequestInit | undefined;
        return init?.method === "PUT";
      });
      expect(putCall).toBeDefined();
    });

    const [putUrl, putInit] = (() => {
      const call = mockFetch.mock.calls.find((c) => (c[1] as RequestInit)?.method === "PUT")!;
      return [call[0] as string, call[1] as RequestInit];
    })();

    expect(putUrl).toBe("/api/admin/quota/default");
    expect(putInit.method).toBe("PUT");
    expect(putInit.credentials).toBe("include");
    const body = JSON.parse(putInit.body as string);
    expect(body.enforce_mode).toBe("hard");
    expect(body.max_tokens).toBe(100_000);
  });
});