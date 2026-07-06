import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PublishButton } from "../PublishButton";

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

describe("PublishButton", () => {
  it("renders a publish trigger button", () => {
    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    expect(
      screen.getByRole("button", { name: /publish/i }),
    ).toBeInTheDocument();
  });

  it("opens the dialog and fetches workspaces on click", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workspaces: [
          { id: "ws-b", name: "Sales" },
          { id: "ws-c", name: "Marketing" },
        ],
      }),
    } as Response);

    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(screen.getByRole("button", { name: /publish/i }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByRole("option", { name: /Sales/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /Marketing/i }),
      ).toBeInTheDocument();
    });
  });

  it("filters out the current workspace from the list", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workspaces: [
          { id: "ws-a", name: "Self" },
          { id: "ws-b", name: "Other" },
        ],
      }),
    } as Response);

    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(screen.getByRole("button", { name: /publish/i }));

    await waitFor(() => {
      expect(
        screen.queryByRole("option", { name: /Self/i }),
      ).not.toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /Other/i }),
      ).toBeInTheDocument();
    });
  });

  it("submits the publish and shows the success status", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          workspaces: [{ id: "ws-b", name: "Sales" }],
        }),
      } as Response) // GET /api/spaces
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          new_thread_id: "T",
          source_thread_id: "A",
          target_workspace_id: "ws-b",
          original_thread_id: "A",
          published_at: "2026-07-06T00:00:00Z",
        }),
      } as Response); // POST /api/threads/A/publish

    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(screen.getByRole("button", { name: /publish/i }));

    await screen.findByRole("dialog");

    const select = await screen.findByRole("combobox");
    await waitFor(() => {
      expect(
        screen.getByRole("option", { name: /Sales/i }),
      ).toBeInTheDocument();
    });
    fireEvent.change(select, { target: { value: "ws-b" } });

    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    expect(await screen.findByText(/published/i)).toBeInTheDocument();
    // POST payload: { target_workspace_id: "ws-b" }
    expect(mockFetch).toHaveBeenCalledTimes(2);
    const [, postInit] = mockFetch.mock.calls[1] as [
      string,
      RequestInit | undefined,
    ];
    expect(postInit?.method).toBe("POST");
    expect(postInit?.body).toBe(
      JSON.stringify({ target_workspace_id: "ws-b" }),
    );
  });

  it("shows Failed status when publish returns non-OK", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          workspaces: [{ id: "ws-b", name: "Sales" }],
        }),
      } as Response) // GET /api/spaces
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: "not found" }),
      } as Response); // POST /api/threads/A/publish -> 404

    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(screen.getByRole("button", { name: /publish/i }));
    await screen.findByRole("dialog");

    const select = await screen.findByRole("combobox");
    await waitFor(() => {
      expect(
        screen.getByRole("option", { name: /Sales/i }),
      ).toBeInTheDocument();
    });
    fireEvent.change(select, { target: { value: "ws-b" } });
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/failed/i);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("disables Confirm button while publish is in flight", async () => {
    // Use a fetch that never resolves during the click; we'll resolve later.
    let resolvePublish!: (value: unknown) => void;
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          workspaces: [{ id: "ws-b", name: "Sales" }],
        }),
      } as Response) // GET /api/spaces
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolvePublish = resolve;
          }),
      ); // POST /api/threads/A/publish (pending)

    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(screen.getByRole("button", { name: /publish/i }));
    await screen.findByRole("dialog");

    const select = await screen.findByRole("combobox");
    await waitFor(() => {
      expect(
        screen.getByRole("option", { name: /Sales/i }),
      ).toBeInTheDocument();
    });
    fireEvent.change(select, { target: { value: "ws-b" } });

    const confirm = screen.getByRole("button", { name: /confirm/i });
    fireEvent.click(confirm);

    // After click but before promise resolves, Confirm should be disabled.
    expect(confirm).toBeDisabled();

    // Resolve the pending publish to clean up.
    resolvePublish({
      ok: true,
      json: async () => ({ new_thread_id: "T" }),
    });
    expect(await screen.findByText(/published/i)).toBeInTheDocument();
  });
});
