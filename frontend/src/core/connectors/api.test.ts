import { describe, it, expect, vi, beforeEach } from "vitest";

import { connectorsApi } from "./api";

describe("connectorsApi", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("list fetches /api/connectors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            connectors: [
              { name: "feishu", display_name: "Feishu (Lark)" },
              { name: "email", display_name: "Email (SMTP/IMAP)" },
            ],
          }),
        ),
      ),
    );
    const { connectors } = await connectorsApi.list();
    expect(connectors).toHaveLength(2);
    expect(connectors[0]?.name).toBe("feishu");
  });

  it("listDLQ respects the limit param", async () => {
    let capturedUrl = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        capturedUrl = String(url);
        return new Response(JSON.stringify({ items: [] }));
      }),
    );
    await connectorsApi.listDLQ(25);
    expect(capturedUrl).toContain("limit=25");
  });

  it("deleteDLQ encodes the id and uses DELETE", async () => {
    let capturedUrl = "";
    let capturedMethod = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        capturedUrl = String(url);
        capturedMethod = init?.method ?? "GET";
        return new Response(null, { status: 204 });
      }),
    );
    await connectorsApi.deleteDLQ("with space");
    expect(capturedUrl).toContain("/api/connectors/dlq/with%20space");
    expect(capturedMethod).toBe("DELETE");
  });

  it("throws on non-2xx with the status code", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 500 })));
    await expect(connectorsApi.list()).rejects.toThrow(/500/);
  });
});
