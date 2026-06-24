import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { identityApi } from "./api";

const originalFetch = globalThis.fetch;

describe("identityApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("listProviders fetches /api/admin/oidc/providers", async () => {
    const mockProviders = [
      {
        id: "p1",
        name: "kc",
        type: "keycloak" as const,
        issuer_url: "https://x",
        client_id: "c",
        enabled: true,
        created_at: "",
      },
    ];
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockProviders), { status: 200 }),
    );
    const result = await identityApi.listProviders();
    expect(result).toHaveLength(1);
    expect(result[0]?.name).toBe("kc");
  });

  it("createProvider sends POST with body", async () => {
    const created = {
      id: "p1",
      name: "kc",
      type: "keycloak" as const,
      issuer_url: "https://x",
      client_id: "c",
      enabled: true,
      created_at: "",
    };
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(created), { status: 201 }),
    );
    const result = await identityApi.createProvider({
      name: "kc",
      type: "keycloak",
      issuer_url: "https://x",
      client_id: "c",
      client_secret: "s",
    });
    expect(result.id).toBe("p1");
  });

  it("throws on non-OK response", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response("not found", { status: 404 }),
    );
    await expect(identityApi.listProviders()).rejects.toThrow(/404/);
  });
});
