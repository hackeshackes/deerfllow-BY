# Development Gateway API Fallback Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make unmatched `/api/*` requests reach the Gateway in `next dev` without intercepting Next.js-owned `/api/auth/*` and `/api/memory/*` route handlers.

**Architecture:** Convert `next.config.js` rewrites from a flat array to Next.js rewrite phases. Keep LangGraph's explicit rewrite in `beforeFiles`, place the Gateway wildcard in `fallback`, and omit it whenever `NEXT_PUBLIC_BACKEND_BASE_URL` is configured. A focused Vitest suite reloads the config under isolated environment combinations and verifies route ownership plus URL normalization.

**Tech Stack:** Next.js 16 rewrites, JavaScript ESM, TypeScript 5.8, Vitest 2, Node.js filesystem APIs, pnpm 10.26.2.

---

## File Structure

- Create `frontend/tests/next-config.test.ts` — owns rewrite-phase regression tests and verifies that local App Router API handlers remain present.
- Modify `frontend/next.config.js:19-53` — constructs `beforeFiles`, `afterFiles`, and `fallback` rewrite phases.
- Modify `CHANGELOG.md` — records the development-mode proxy correction under the current unreleased section, if that section exists; otherwise add a concise `Unreleased` heading without changing historical release notes.

### Task 1: Add failing rewrite contract tests

**Files:**
- Create: `frontend/tests/next-config.test.ts`
- Test: `frontend/tests/next-config.test.ts`

- [x] **Step 1: Create an environment-isolated config loader and the first failing Gateway fallback test**

Create `frontend/tests/next-config.test.ts` with:

```ts
import { existsSync } from "node:fs";
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

  const module = (await import("../next.config.js")) as {
    default: NextConfigUnderTest;
  };
  return module.default.rewrites();
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
});
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd frontend && pnpm vitest run tests/next-config.test.ts
```

Expected: FAIL because current `rewrites()` returns an array, so `rewrites.fallback` is `undefined`.

- [x] **Step 3: Add the remaining failing contract tests**

Append these tests inside the existing `describe` block:

```ts
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
    const frontendRoot = fileURLToPath(new URL("..", import.meta.url));
    const localRouteHandlers = [
      "src/app/api/auth/[...all]/route.ts",
      "src/app/api/memory/route.ts",
      "src/app/api/memory/[...path]/route.ts",
    ];

    expect(
      localRouteHandlers.map((routePath) =>
        existsSync(fileURLToPath(new URL(routePath, `${frontendRoot}/`))),
      ),
    ).toEqual([true, true, true]);
  });
```

- [x] **Step 4: Re-run the focused test and verify all rewrite assertions remain RED**

Run:

```bash
cd frontend && pnpm vitest run tests/next-config.test.ts
```

Expected: the filesystem ownership test passes; rewrite-phase tests fail because the implementation still returns a flat array.

- [x] **Step 5: Commit the RED tests**

```bash
git add frontend/tests/next-config.test.ts
git commit -m "test: cover development API fallback rewrites"
```

### Task 2: Implement phased fallback rewrites

**Files:**
- Modify: `frontend/next.config.js:19-53`
- Test: `frontend/tests/next-config.test.ts`

- [x] **Step 1: Replace the flat rewrite array with phased rewrite collections**

Replace the `rewrites()` body in `frontend/next.config.js` with:

```js
  async rewrites() {
    const beforeFiles = [];
    const fallback = [];
    const langgraphURL = getInternalServiceURL(
      "DEER_FLOW_INTERNAL_LANGGRAPH_BASE_URL",
      "http://127.0.0.1:2024",
    );
    const gatewayURL = getInternalServiceURL(
      "DEER_FLOW_INTERNAL_GATEWAY_BASE_URL",
      "http://127.0.0.1:8001",
    );

    if (!process.env.NEXT_PUBLIC_LANGGRAPH_BASE_URL) {
      beforeFiles.push({
        source: "/api/langgraph",
        destination: langgraphURL,
      });
      beforeFiles.push({
        source: "/api/langgraph/:path*",
        destination: `${langgraphURL}/:path*`,
      });
    }

    if (!process.env.NEXT_PUBLIC_BACKEND_BASE_URL) {
      fallback.push({
        source: "/api/:path*",
        destination: `${gatewayURL}/api/:path*`,
      });
    }

    return {
      beforeFiles,
      afterFiles: [],
      fallback,
    };
  },
```

This intentionally removes the `/api/agents` special cases because the Gateway fallback now covers them.

- [x] **Step 2: Run the focused tests and verify GREEN**

Run:

```bash
cd frontend && pnpm vitest run tests/next-config.test.ts
```

Expected: all six tests PASS.

- [x] **Step 3: Run frontend formatting on the touched files**

Run:

```bash
cd frontend && pnpm prettier --write next.config.js tests/next-config.test.ts
```

Expected: command exits 0 and reports both files formatted or unchanged.

- [x] **Step 4: Re-run the focused tests after formatting**

Run:

```bash
cd frontend && pnpm vitest run tests/next-config.test.ts
```

Expected: all six tests PASS.

- [x] **Step 5: Commit the implementation**

```bash
git add frontend/next.config.js frontend/tests/next-config.test.ts
git commit -m "fix: proxy unmatched development APIs to gateway"
```

### Task 3: Document and verify the fix

**Files:**
- Modify: `CHANGELOG.md`
- Verify: `frontend/next.config.js`
- Verify: `frontend/tests/next-config.test.ts`

- [x] **Step 1: Replace the placeholder Unreleased subsection with the fix entry**

Replace this current block in `CHANGELOG.md`:

```markdown
### 计划中

暂未启动。
```

with:

```markdown
### Fixed

- Fixed frontend development mode so unmatched `/api/*` requests fall back to the Gateway while Next.js-owned `/api/auth/*` and `/api/memory/*` handlers remain local.
```

Do not modify historical release entries.

- [x] **Step 2: Run the complete frontend quality gate**

Run:

```bash
cd frontend && pnpm check
```

Expected: ESLint, TypeScript, and the full Vitest suite exit 0.

- [x] **Step 3: Run the production frontend build**

Run:

```bash
cd frontend && pnpm build
```

Expected: Next.js production build exits 0. No route conflict or invalid rewrite error is reported.

- [x] **Step 4: Inspect the final diff and whitespace**

Run:

```bash
git diff --check
git diff -- frontend/next.config.js frontend/tests/next-config.test.ts CHANGELOG.md
git status --short
```

Expected: `git diff --check` exits 0; the diff contains only the phased rewrites, focused tests, and changelog entry.

- [x] **Step 5: Request mandatory code reviews**

Dispatch these read-only reviewers in parallel against the final diff:

- `code-reviewer` for general correctness and maintainability.
- `typescript-reviewer` for the Vitest/TypeScript test code.
- `react-reviewer` only if any `.tsx` or React logic was touched; for this plan it should be skipped because no React files change.

Expected: no CRITICAL or HIGH findings. Resolve any verified issue, then repeat `pnpm check` and `pnpm build`.

- [x] **Step 6: Commit documentation and verified closeout**

```bash
git add CHANGELOG.md
git commit -m "docs: note development gateway fallback proxy"
```

### Task 4: Publish the fix and close Issue #1

**Status: DEFERRED — already merged directly to `main`.**

The implementation, tests, and changelog entry were committed directly to `main` as
`21759b40` (`fix: proxy unmatched development APIs to gateway`) and pushed to
`origin/main`. Issue #1 was closed on `2026-07-24`. Because the change is already
released, the original publishing path (feature branch → PR → merge authorization)
does not apply and is intentionally skipped. A PR-from-`main` would be an empty
diff.

The steps below are preserved for historical reference only; they were **not** run.

> Reference-only (not executed):
> 1. ~Confirm a non-`main` implementation branch exists — not the case; work went straight to `main`.~
> 2. ~`git push -u origin <branch-name>` — superseded by the `origin/main` push in `2176b40`.~
> 3. ~`gh pr create ... --title "fix: proxy unmatched development APIs to gateway"` — not created; Issue #1 closed via direct merge.~
> 4. ~`gh pr checks` / `gh pr view` — N/A.~
> 5. Stop for merge authorization — the merge already occurred on `main`; a re-merge would be a no-op.
