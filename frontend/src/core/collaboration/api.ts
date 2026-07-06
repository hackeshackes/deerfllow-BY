/**
 * Cross-workspace publish: list target workspaces and publish a thread.
 *
 * Endpoint surface mirrors the backend scaffold in C1:
 *   GET  /api/spaces                 -> { workspaces: [...] } | { items: [...] }
 *   POST /api/threads/{id}/publish   -> { new_thread_id, source_thread_id,
 *                                          target_workspace_id, original_thread_id,
 *                                          published_at }
 */

export type Workspace = {
  id: string;
  name: string;
};

type PublishResponse = {
  new_thread_id: string;
  source_thread_id?: string;
  target_workspace_id?: string;
  original_thread_id?: string;
  published_at?: string;
};

export async function listWorkspaces(): Promise<Workspace[]> {
  const response = await fetch("/api/spaces");
  if (!response.ok) {
    throw new Error(`spaces ${response.status}`);
  }
  const body = (await response.json()) as {
    workspaces?: Workspace[];
    items?: Workspace[];
  };
  return body.workspaces ?? body.items ?? [];
}

export async function publishThread(
  threadId: string,
  targetWorkspaceId: string,
): Promise<PublishResponse> {
  const response = await fetch(
    `/api/threads/${encodeURIComponent(threadId)}/publish`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_workspace_id: targetWorkspaceId }),
    },
  );
  if (!response.ok) {
    throw new Error(`publish ${response.status}`);
  }
  return (await response.json()) as PublishResponse;
}
