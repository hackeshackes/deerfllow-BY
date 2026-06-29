import type { Space } from "./types";

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    credentials: "include",
  });
  if (!resp.ok) {
    throw new Error(`${resp.status}: ${await resp.text()}`);
  }
  return resp.json() as Promise<T>;
}

export const spacesApi = {
  /** List all spaces the current user has access to. */
  list: () => fetchJSON<{ spaces: Space[] }>("/api/spaces"),

  /**
   * Get the current space. The optional `spaceId` is sent as the
   * `X-MicX-Space` header so the server can resolve cookie- or header-driven
   * scope state.
   */
  current: (spaceId?: string) => {
    const headers: Record<string, string> = {};
    if (spaceId) headers["X-MicX-Space"] = spaceId;
    return fetchJSON<Space>("/api/spaces/current", { headers });
  },

  /** Look up a single space by id. */
  get: (spaceId: string) => fetchJSON<Space>(`/api/spaces/${encodeURIComponent(spaceId)}`),
};
