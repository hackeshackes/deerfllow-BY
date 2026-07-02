import { afterEach, describe, expect, it, vi } from "vitest";

import { multitenancyApi } from "../api";

const originalFetch = globalThis.fetch;

describe("multitenancyApi", () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("costSummary fetches /api/admin/cost/summary with tenant_id", async () => {
    const mockSummary = {
      tenant_id: "default",
      total_tokens: 1000,
      total_requests: 5,
      by_tenant: [{ entity_id: "default", total_tokens: 1000, request_count: 5 }],
      by_user: [],
      by_model: [
        { entity_id: "gpt-4", total_tokens: 1000, request_count: 5 },
      ],
    };
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(mockSummary), { status: 200 }),
      );

    const result = await multitenancyApi.costSummary("default");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/admin/cost/summary?tenant_id=default");
    expect(init.credentials).toBe("include");
    expect(result.tenant_id).toBe("default");
    expect(result.total_tokens).toBe(1000);
    expect(result.by_model[0]?.entity_id).toBe("gpt-4");
  });

  it("getQuota fetches /api/admin/quota/{tenant_id}", async () => {
    const mockQuota = {
      tenant_id: "default",
      max_tokens: 5000,
      max_rpm: 10,
      period: "monthly" as const,
      enforce_mode: "advisory" as const,
    };
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(mockQuota), { status: 200 }),
      );

    const result = await multitenancyApi.getQuota("default");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/admin/quota/default");
    expect(init.credentials).toBe("include");
    expect(result.max_tokens).toBe(5000);
    expect(result.enforce_mode).toBe("advisory");
  });

  it("setQuota PUTs JSON body to /api/admin/quota/{tenant_id}", async () => {
    const mockResponse = {
      tenant_id: "default",
      max_tokens: 8000,
      max_rpm: 20,
      period: "daily" as const,
      enforce_mode: "hard" as const,
    };
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(mockResponse), { status: 200 }),
      );

    const result = await multitenancyApi.setQuota("default", {
      max_tokens: 8000,
      max_rpm: 20,
      period: "daily",
      enforce_mode: "hard",
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/admin/quota/default");
    expect(init.method).toBe("PUT");
    expect(init.credentials).toBe("include");
    expect(init.headers).toMatchObject({ "Content-Type": "application/json" });
    expect(init.body).toBe(
      JSON.stringify({
        max_tokens: 8000,
        max_rpm: 20,
        period: "daily",
        enforce_mode: "hard",
      }),
    );
    expect(result.enforce_mode).toBe("hard");
  });
});