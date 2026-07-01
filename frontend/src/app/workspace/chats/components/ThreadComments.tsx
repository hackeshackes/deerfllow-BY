"use client";

import { useEffect, useState } from "react";

import { MentionInput } from "./MentionInput";

interface ApiComment {
  id: string;
  thread_id: string;
  author_id: string;
  text: string;
  source: string;
  parent_comment_id: string | null;
  mentioned_user_ids: string[];
  created_at: string;
}

type FetchFn = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

interface ThreadCommentsProps {
  threadId: string;
  /** Override the API URL — used in tests. */
  fetchUrl?: string;
  /** Override posted author_id. Defaults to "anonymous". */
  authorId?: string;
  /** Override fetcher for tests; defaults to global `fetch`. */
  fetcher?: FetchFn;
  emptyText?: string;
}

/**
 * Thread-level comments panel. Fetches + posts to the v1.5.8
 * ``/api/threads/{thread_id}/comments`` endpoints. Reuses the existing
 * ``MentionInput`` for the input box so the @-trigger autocomplete
 * stays consistent between chat messages and comments.
 */
export function ThreadComments({
  threadId,
  fetchUrl,
  authorId: _authorId = "anonymous",
  fetcher = (input, init) => fetch(input, init),
  emptyText = "No comments yet — be the first.",
}: ThreadCommentsProps) {
  const [comments, setComments] = useState<ApiComment[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const url = fetchUrl ?? `/api/threads/${threadId}/comments`;

  const reload = async () => {
    try {
      const r = await fetcher(url, { credentials: "include" });
      if (r.ok) {
        const body = (await r.json()) as unknown;
        if (Array.isArray(body)) setComments(body as ApiComment[]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  useEffect(() => {
    void reload();
    // reload is recreated on each render but its content depends only on
    // threadId; lint exemption is intentional.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  const submit = async () => {
    if (!draft.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const r = await fetcher(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ text: draft }),
      });
      if (!r.ok) throw new Error(`POST failed: ${r.status}`);
      setDraft("");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      data-testid="thread-comments"
      className="flex flex-col gap-3 p-3"
    >
      <h3 className="text-sm font-medium">Comments</h3>
      {error && (
        <p className="text-xs text-red-600" data-testid="thread-comments-error">
          {error}
        </p>
      )}
      <ol className="flex flex-col gap-2">
        {comments.length === 0 ? (
          <li
            data-testid="thread-comments-empty"
            className="text-muted-foreground text-xs italic"
          >
            {emptyText}
          </li>
        ) : (
          comments.map((c) => (
            <li
              key={c.id}
              data-testid={`thread-comment-${c.id}`}
              className="rounded border p-2 text-sm"
            >
              <div className="text-muted-foreground text-xs">
                {c.author_id} ·{" "}
                {new Date(c.created_at).toLocaleString()}
              </div>
              <p className="mt-1">{c.text}</p>
            </li>
          ))
        )}
      </ol>
      <MentionInput
        value={draft}
        onChange={setDraft}
        placeholder="Add a comment…"
        suggestions={[] as ReadonlyArray<string>}
      />
      <button
        type="button"
        data-testid="thread-comment-submit"
        disabled={loading || !draft.trim()}
        onClick={() => void submit()}
        className="bg-primary text-primary-foreground rounded px-3 py-1 text-sm disabled:opacity-50"
      >
        {loading ? "Posting…" : "Post comment"}
      </button>
    </section>
  );
}
