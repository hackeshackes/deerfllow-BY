"use client";
import { useEffect, useState } from "react";

import { multitenancyApi, type UsageSummary } from "../api";

export function useCostSummary(tenantId: string) {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    multitenancyApi
      .costSummary(tenantId)
      .then(setSummary)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : String(e)),
      )
      .finally(() => setLoading(false));
  }, [tenantId]);

  return { summary, loading, error };
}