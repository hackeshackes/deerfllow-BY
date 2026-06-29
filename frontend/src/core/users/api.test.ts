import { describe, it, expect, vi, beforeEach } from "vitest";

import { usersApi } from "./api";

describe("usersApi", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("search sends q when provided", async () => {
    let capturedUrl = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        capturedUrl = String(url);
        return new Response(JSON.stringify({ users: [] }));
      }),
    );
    await usersApi.search("ali");
    expect(capturedUrl).toContain("/api/users/search");
    expect(capturedUrl).toContain("q=ali");
  });

  it("search omits q when empty", async () => {
    let capturedUrl = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        capturedUrl = String(url);
        return new Response(JSON.stringify({ users: [] }));
      }),
    );
    await usersApi.search("");
    expect(capturedUrl).not.toContain("q=");
  });

  it("search respects the limit param", async () => {
    let capturedUrl = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        capturedUrl = String(url);
        return new Response(JSON.stringify({ users: [] }));
      }),
    );
    await usersApi.search("x", 25);
    expect(capturedUrl).toContain("limit=25");
  });

  it("search returns the users array", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            users: [
              { id: "u1", handle: "@alice", displayName: "Alice" },
              { id: "u2", handle: "@bob", displayName: "Bob", email: "b@x" },
            ],
          }),
        ),
      ),
    );
    const users = await usersApi.search("a");
    expect(users).toHaveLength(2);
    expect(users[0]?.handle).toBe("@alice");
    expect(users[1]?.email).toBe("b@x");
  });

  it("throws on non-2xx with the status code", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 503 })));
    await expect(usersApi.search("x")).rejects.toThrow(/503/);
  });
});
