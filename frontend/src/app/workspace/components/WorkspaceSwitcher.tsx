"use client";

import { useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import { useSpaces } from "@/core/spaces/hooks/use-spaces";

const COOKIE_NAME = "micx_space";
const COOKIE_MAX_AGE = 60 * 60 * 24; // 1 day

/**
 * Top-level space switcher. Renders a `<select>` of all spaces the user
 * can access; on change, persists the choice to a cookie and refreshes
 * the server-rendered tree so the rest of the app picks up the new scope.
 */
export function WorkspaceSwitcher({ currentSpaceId }: { currentSpaceId?: string }) {
  const { spaces, isLoading } = useSpaces();
  const router = useRouter();
  const [selected, setSelected] = useState<string>(currentSpaceId ?? "personal");

  useEffect(() => {
    if (currentSpaceId) setSelected(currentSpaceId);
  }, [currentSpaceId]);

  if (isLoading) {
    return <div data-testid="workspace-switcher-loading">Loading spaces…</div>;
  }

  return (
    <select
      data-testid="workspace-switcher"
      className="rounded border bg-white p-2"
      value={selected}
      onChange={(e) => {
        const id = e.target.value;
        setSelected(id);
        // Persist so SSR picks the same scope on next request.
        document.cookie = `${COOKIE_NAME}=${encodeURIComponent(id)}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
        router.refresh();
      }}
    >
      {spaces.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name}
        </option>
      ))}
    </select>
  );
}
