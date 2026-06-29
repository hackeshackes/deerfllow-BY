"use client";

import { useEffect, useState } from "react";

import { spacesApi } from "../api";
import type { Space } from "../types";

interface UseSpacesResult {
  spaces: Space[];
  loading: boolean;
  error: string | null;
}

/** Fetch the list of spaces the current user has access to. */
export function useSpaces(): UseSpacesResult {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    spacesApi
      .list()
      .then((res) => {
        if (!cancelled) setSpaces(res.spaces);
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
  }, []);

  return { spaces, loading, error };
}
