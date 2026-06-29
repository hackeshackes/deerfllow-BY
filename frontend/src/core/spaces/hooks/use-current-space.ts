"use client";

import { useEffect, useState } from "react";

import { spacesApi } from "../api";
import type { Space } from "../types";

interface UseCurrentSpaceResult {
  space: Space | null;
  isLoading: boolean;
  error: string | null;
}

/**
 * Read the current space. Pass `spaceId` to switch the resolution explicitly
 * (the `X-MicX-Space` header will be set). When omitted, the server falls
 * back to the cookie/default — typically `personal`.
 */
export function useCurrentSpace(spaceId?: string): UseCurrentSpaceResult {
  const [space, setSpace] = useState<Space | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    spacesApi
      .current(spaceId)
      .then((s) => {
        if (!cancelled) setSpace(s);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [spaceId]);

  return { space, isLoading: loading, error };
}
