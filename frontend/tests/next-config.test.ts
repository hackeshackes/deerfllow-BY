import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it, vi } from "vitest";

interface RewriteRule {
  source: string;
  destination: string;
}

interface RewritePhases {
  beforeFiles: RewriteRule[];
  afterFiles: RewriteRule[];
  fallback: RewriteRule[];
}

interface NextConfigUnderTest {
  rewrites(): Promise<RewritePhases>;
}

const ORIGINAL_ENV = { ...process.env };

async function loadRewrites(
  overrides: Readonly<Record<string, string | undefined>> = {},
): Promise<RewritePhases> {
  vi.resetModules();
  process.env = {
    ...ORIGINAL_ENV,
    NODE_ENV: "test",
    SKIP_ENV_VALIDATION: "1",
  };

  for (const [key, value] of Object.entries(overrides)) {
    if (value === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = value;
    }
  }

  const nextConfig = (await import("../next.config.js")) as {
    default: NextConfigUnderTest;
  };
  return nextConfig.default.rewrites();
}

afterEach(() => {
  process.env = { ...ORIGINAL_ENV };
  vi.restoreAllMocks();
});

describe("Next.js API rewrites", () => {
  it("falls back unmatched API requests to the default Gateway", async () => {
    const rewrites = await loadRewrites({
      NEXT_PUBLIC_BACKEND_BASE_URL: undefined,
      DEER_FLOW_INTERNAL_GATEWAY_BASE_URL: undefined,
    });

    expect(rewrites.fallback).toContainEqual({
      source: "/api/:path*",
      destination: "http://127.0.0.1:8001/api/:path*",
    });
    expect(rewrites.afterFiles).toEqual([]);
  });

  it("normalizes a configured internal Gateway URL", async () => {
    const rewrites = await loadRewrites({
      NEXT_PUBLIC_BACKEND_BASE_URL: undefined,
      DEER_FLOW_INTERNAL_GATEWAY_BASE_URL: "http://gateway.internal:9000///",
    });

    expect(rewrites.fallback).toEqual([
      {
        source: "/api/:path*",
        destination: "http://gateway.internal:9000/api/:path*",
      },
    ]);
  });

  it("omits the Gateway fallback when a public backend URL is configured", async () => {
    const rewrites = await loadRewrites({
      NEXT_PUBLIC_BACKEND_BASE_URL: "https://gateway.example.com",
    });

    expect(rewrites.fallback).toEqual([]);
  });

  it("keeps LangGraph rewrites in beforeFiles", async () => {
    const rewrites = await loadRewrites({
      NEXT_PUBLIC_LANGGRAPH_BASE_URL: undefined,
      DEER_FLOW_INTERNAL_LANGGRAPH_BASE_URL: "http://langgraph.internal:2024/",
    });

    expect(rewrites.beforeFiles).toEqual([
      {
        source: "/api/langgraph",
        destination: "http://langgraph.internal:2024",
      },
      {
        source: "/api/langgraph/:path*",
        destination: "http://langgraph.internal:2024/:path*",
      },
    ]);
  });

  it("omits LangGraph rewrites when a public URL is configured", async () => {
    const rewrites = await loadRewrites({
      NEXT_PUBLIC_LANGGRAPH_BASE_URL: "https://langgraph.example.com",
    });

    expect(rewrites.beforeFiles).toEqual([]);
  });

  it("keeps frontend-owned API route handlers in the filesystem", () => {
    // happy-dom replaces the URL constructor used in `new URL("..", import.meta.url)`,
    // so resolve the directory through path.dirname + fileURLToPath explicitly.
    const frontendRoot = path.dirname(
      path.dirname(fileURLToPath(import.meta.url)),
    );
    const localRouteHandlers = [
      "src/app/api/auth/[...all]/route.ts",
      "src/app/api/memory/route.ts",
      "src/app/api/memory/[...path]/route.ts",
    ];

    expect(
      localRouteHandlers.map((routePath) =>
        existsSync(path.join(frontendRoot, routePath)),
      ),
    ).toEqual([true, true, true]);
  });
});
