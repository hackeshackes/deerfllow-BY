import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ThreadComments } from "./ThreadComments";

type FetchFn = typeof fetch;
type MockedFetch = ReturnType<typeof vi.fn>;

let mockFetch: MockedFetch;
beforeEach(() => {
  mockFetch = vi.fn();
  global.fetch = mockFetch as unknown as FetchFn;
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ThreadComments", () => {
  it("renders the empty state when there are no comments", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response);

    render(<ThreadComments threadId="t-1" />);

    expect(
      await screen.findByTestId("thread-comments-empty"),
    ).toBeInTheDocument();
    expect(screen.getByText(/No comments yet/i)).toBeInTheDocument();
  });

  it("submits a comment and refreshes the list", async () => {
    mockFetch
      // initial GET
      .mockResolvedValueOnce({ ok: true, json: async () => [] } as Response)
      // POST
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "c-1",
          thread_id: "t-1",
          author_id: "anonymous",
          text: "hi",
          source: "user",
          parent_comment_id: null,
          mentioned_user_ids: [],
          created_at: "2026-07-01T00:00:00Z",
        }),
      } as Response)
      // reload GET
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            id: "c-1",
            thread_id: "t-1",
            author_id: "alice",
            text: "hi",
            source: "user",
            parent_comment_id: null,
            mentioned_user_ids: [],
            created_at: "2026-07-01T00:00:00Z",
          },
        ],
      } as Response);

    render(<ThreadComments threadId="t-1" />);

    const input = await screen.findByPlaceholderText(/Add a comment/i);
    fireEvent.change(input, { target: { value: "hi" } });
    fireEvent.click(screen.getByTestId("thread-comment-submit"));

    await waitFor(() => screen.getByTestId("thread-comment-c-1"));
    expect(screen.getByText("hi")).toBeInTheDocument();
  });

  it("disables submit while a request is in flight", async () => {
    let resolvePost: ((value: unknown) => void) | undefined;
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => [] } as Response) // GET
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolvePost = resolve;
        }),
      ); // POST pending

    render(<ThreadComments threadId="t-1" />);
    const input = await screen.findByPlaceholderText(/Add a comment/i);
    fireEvent.change(input, { target: { value: "queued" } });

    const btn = screen.getByTestId("thread-comment-submit");
    fireEvent.click(btn);
    // After click, loading=true and button is disabled.
    expect(btn).toBeDisabled();

    // Cleanup: resolve the pending POST so any leftover awaits settle.
    if (resolvePost) {
      resolvePost({
        ok: true,
        json: async () => ({}),
      });
    }
  });

  it("shows an error when initial fetch fails", async () => {
    mockFetch.mockRejectedValueOnce(new Error("network down"));

    render(<ThreadComments threadId="t-1" />);

    const errEl = await screen.findByTestId("thread-comments-error");
    expect(errEl.textContent).toMatch(/network down/);
  });
});
