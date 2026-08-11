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

function mockSpaces(workspaces: { id: string; name: string }[]) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ workspaces }),
  } as Response);
}

describe("PublishButton — visibility gating", () => {
  it("renders the trigger when there is a target workspace to publish into", async () => {
    mockSpaces([{ id: "ws-b", name: "Sales" }]);
    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    expect(
      await screen.findByRole("button", { name: /publish/i }),
    ).toBeInTheDocument();
  });

  it("hides the button when only the current workspace exists", async () => {
    mockSpaces([{ id: "ws-a", name: "Self" }]);
    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    // Wait for the prefetch to settle (no button should ever appear).
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(
      screen.queryByRole("button", { name: /publish/i }),
    ).not.toBeInTheDocument();
  });

  it("hides when the prefetch fails (dereference, don't show broken UI)", async () => {
    mockFetch.mockRejectedValueOnce(new Error("network"));
    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(
      screen.queryByRole("button", { name: /publish/i }),
    ).not.toBeInTheDocument();
  });
});

describe("PublishButton — dialog flow (list prefetched on mount)", () => {
  it("opens a dialog with the prefetched target workspaces", async () => {
    mockSpaces([
      { id: "ws-b", name: "Sales" },
      { id: "ws-c", name: "Marketing" },
    ]);
    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(
      await screen.findByRole("button", { name: /publish/i }),
    );

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.getByRole("option", { name: /Sales/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /Marketing/i }),
      ).toBeInTheDocument();
    });
    // No second fetch when opening (list is reused).
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("filters out the current workspace from the list", async () => {
    mockSpaces([
      { id: "ws-a", name: "Self" },
      { id: "ws-b", name: "Other" },
    ]);
    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(await screen.findByRole("button", { name: /publish/i }));
    await screen.findByRole("dialog");

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
    // 1 x GET /api/spaces (mount) + 1 x POST /api/threads/A/publish.
    mockSpaces([{ id: "ws-b", name: "Sales" }]);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        new_thread_id: "T",
        source_thread_id: "A",
        target_workspace_id: "ws-b",
        original_thread_id: "A",
        published_at: "2026-07-06T00:00:00Z",
      }),
    } as Response);

    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(await screen.findByRole("button", { name: /publish/i }));
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
    mockSpaces([{ id: "ws-b", name: "Sales" }]);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "not found" }),
    } as Response);

    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(await screen.findByRole("button", { name: /publish/i }));
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
    mockSpaces([{ id: "ws-b", name: "Sales" }]);
    let resolvePublish!: (value: unknown) => void;
    mockFetch.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolvePublish = resolve;
        }),
    ); // POST (pending)

    render(<PublishButton threadId="A" currentWorkspaceId="ws-a" />);

    fireEvent.click(await screen.findByRole("button", { name: /publish/i }));
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

    expect(confirm).toBeDisabled();

    resolvePublish({ ok: true, json: async () => ({ new_thread_id: "t" }) });
    expect(await screen.findByText(/published/i)).toBeInTheDocument();
  });
});