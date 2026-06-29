/** User suggestion surfaced by the mention autocomplete. */
export interface UserSuggestion {
  id: string;
  /** Display label shown in the dropdown (typically the @handle). */
  handle: string;
  /** Friendly name shown alongside the handle. */
  displayName: string;
  /** Optional email; surfaced in the dropdown title attribute. */
  email?: string;
}

interface UsersSearchResponse {
  users: UserSuggestion[];
}

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

/**
 * Search users by free-text query. The backend scopes to users visible
 * in the current workspace; an empty `query` returns the first page of
 * recent collaborators (useful for "mention someone I worked with").
 */
export const usersApi = {
  search: async (query: string, limit = 10): Promise<UserSuggestion[]> => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (query) params.set("q", query);
    const url = `/api/users/search?${params.toString()}`;
    const data = await fetchJSON<UsersSearchResponse>(url);
    return data.users;
  },
};
