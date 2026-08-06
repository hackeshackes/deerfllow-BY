# Development Gateway API Fallback Proxy Design

**Date:** 2026-07-24  
**Issue:** [#1 — Missing API Route Proxies in Frontend Development Mode](https://github.com/hackeshackes/deerfllow-BY/issues/1)

## Problem

When the frontend runs with `pnpm dev` and `NEXT_PUBLIC_BACKEND_BASE_URL` is unset, `frontend/next.config.js` proxies only `/api/agents*` to the Gateway. Browser requests such as `/api/session/login`, `/api/users/*`, and `/api/workspaces/*` therefore resolve against the Next.js development server and return 404.

A regular `/api/:path*` rewrite is unsafe because this frontend also owns local App Router handlers under `/api/auth/*` and `/api/memory/*`. A normal rewrite can intercept those routes before the filesystem router handles them.

## Goals

- Proxy any otherwise-unmatched `/api/*` request to the Gateway during local development.
- Preserve Next.js-owned `/api/auth/*` and `/api/memory/*` handlers.
- Preserve the separate LangGraph proxy behavior.
- Avoid maintaining a duplicated list of Gateway route prefixes.
- Keep explicit public backend URL behavior unchanged.

## Non-goals

- Changing production Nginx routing.
- Replacing local Next.js API handlers.
- Changing Gateway authentication, cookies, CORS, or API contracts.
- Adding a general-purpose proxy implementation in application code.

## Design

### Rewrite phases

Change `rewrites()` to return Next.js' phase object:

```js
{
  beforeFiles: [...],
  afterFiles: [],
  fallback: [...],
}
```

1. If `NEXT_PUBLIC_LANGGRAPH_BASE_URL` is unset, place the existing `/api/langgraph` mappings in `beforeFiles`. LangGraph remains a deliberate override because it is a separate service and has an existing path transformation contract.
2. If `NEXT_PUBLIC_BACKEND_BASE_URL` is unset, add one rule to `fallback`:

   ```text
   /api/:path* -> <internal-gateway>/api/:path*
   ```

3. Remove the now-redundant `/api/agents` special cases. The fallback rule covers them after local filesystem routes have had a chance to match.

Next.js evaluates fallback rewrites only after filesystem routes and `afterFiles` rewrites. Therefore `/api/auth/*` and `/api/memory/*` remain local, while `/api/session/*`, `/api/users/*`, `/api/workspaces/*`, and future Gateway paths are forwarded.

### Environment behavior

`getInternalServiceURL()` remains the single normalization helper:

- `DEER_FLOW_INTERNAL_GATEWAY_BASE_URL`, default `http://127.0.0.1:8001`
- `DEER_FLOW_INTERNAL_LANGGRAPH_BASE_URL`, default `http://127.0.0.1:2024`
- trailing slashes removed before destinations are constructed

If the corresponding `NEXT_PUBLIC_*` URL is configured, Next does not add that internal proxy rule, preserving existing deployment behavior.

## Error handling

The rewrite layer does not transform Gateway errors. Connection failures and Gateway HTTP responses pass through Next.js' proxy behavior. This keeps error semantics aligned with the upstream service and avoids inventing a second response envelope.

Invalid or blank internal service URLs continue to use the existing fallback URL behavior. URL validation remains governed by the frontend environment schema and current startup checks.

## Testing

Add a focused Vitest suite for `next.config.js` that controls environment variables and reloads the module for each case.

Required assertions:

1. With no public backend URL, `fallback` contains `/api/:path*` mapped to the default Gateway URL.
2. With `DEER_FLOW_INTERNAL_GATEWAY_BASE_URL` configured with trailing slashes, the destination is normalized.
3. With `NEXT_PUBLIC_BACKEND_BASE_URL` configured, no Gateway fallback rule is generated.
4. Existing LangGraph rules remain in `beforeFiles` when its public URL is unset and disappear when it is set.
5. The repository still contains local handlers for `/api/auth/[...all]`, `/api/memory`, and `/api/memory/[...path]`; combined with fallback-phase placement, this protects route ownership from regression.

Verification:

- Run the focused rewrite test in RED before implementation.
- Run the focused test after implementation.
- Run `pnpm check` from `frontend/`.
- Run `pnpm build` from `frontend/`.

## GitHub closeout

After the fix is verified and committed:

- Comment on Issue #1 with the fixing commit and explain that the Gateway proxy now uses fallback rewrites so local Next API handlers remain intact.
- Close Issue #1.

No unrelated repository settings, routes, or production proxy configuration are included in this change.
