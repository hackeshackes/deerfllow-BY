import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ConnectorsAdminPage } from "./connectors-admin-page";

function mockFetch(handlers: Record<string, () => unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      const method = (init?.method ?? "GET").toUpperCase();
      const key = `${method} ${u.split("?")[0]}`;
      const handler = handlers[key];
      if (!handler) {
        return new Response("not mocked", { status: 599 });
      }
      return new Response(typeof handler() === "string" ? (handler() as string) : JSON.stringify(handler()));
    }),
  );
}

describe("ConnectorsAdminPage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders registered connectors from the API", async () => {
    mockFetch({
      "GET /api/connectors": () => ({
        connectors: [
          { name: "feishu", display_name: "Feishu (Lark)" },
          { name: "dingtalk", display_name: "DingTalk" },
          { name: "wecom", display_name: "WeCom" },
          { name: "email", display_name: "Email (SMTP/IMAP)" },
        ],
      }),
      "GET /api/connectors/dlq": () => ({ items: [] }),
    });
    render(<ConnectorsAdminPage />);
    await waitFor(() => expect(screen.getByTestId("connector-feishu")).toBeInTheDocument());
    expect(screen.getByTestId("connector-feishu")).toHaveTextContent("Feishu (Lark)");
    expect(screen.getByTestId("connector-dingtalk")).toBeInTheDocument();
    expect(screen.getByTestId("connector-wecom")).toBeInTheDocument();
    expect(screen.getByTestId("connector-email")).toBeInTheDocument();
  });

  it("renders empty state when no connectors are registered", async () => {
    mockFetch({
      "GET /api/connectors": () => ({ connectors: [] }),
      "GET /api/connectors/dlq": () => ({ items: [] }),
    });
    render(<ConnectorsAdminPage />);
    await waitFor(() =>
      expect(screen.getByText("No connectors registered yet.")).toBeInTheDocument(),
    );
  });

  it("shows DLQ items and removes one on Drop", async () => {
    let dlqItems = [
      {
        id: "dlq-1",
        connector: "feishu",
        error: "timeout",
        attempts: 3,
        timestamp: "2026-06-29T10:00:00Z",
        message: { text: "hi" },
      },
      {
        id: "dlq-2",
        connector: "email",
        error: "smtp down",
        attempts: 2,
        timestamp: "2026-06-29T10:01:00Z",
      },
    ];
    mockFetch({
      "GET /api/connectors": () => ({ connectors: [] }),
      "GET /api/connectors/dlq": () => ({ items: dlqItems }),
      "DELETE /api/connectors/dlq/dlq-1": () => {
        dlqItems = dlqItems.filter((d) => d.id !== "dlq-1");
        return "";
      },
    });
    render(<ConnectorsAdminPage />);
    await waitFor(() => expect(screen.getByTestId("dlq-dlq-1")).toBeInTheDocument());
    expect(screen.getByTestId("dlq-dlq-1")).toHaveTextContent("timeout");
    expect(screen.getByTestId("dlq-dlq-2")).toBeInTheDocument();

    // Click Drop on the first DLQ item
    const dropButtons = screen.getAllByRole("button", { name: /drop/i });
    fireEvent.click(dropButtons[0]!);

    await waitFor(() => expect(screen.queryByTestId("dlq-dlq-1")).not.toBeInTheDocument());
    expect(screen.getByTestId("dlq-dlq-2")).toBeInTheDocument();
  });

  it("surfaces an error message when the API fails", async () => {
    mockFetch({
      "GET /api/connectors": () => {
        throw new Error("boom");
      },
      "GET /api/connectors/dlq": () => ({ items: [] }),
    });
    render(<ConnectorsAdminPage />);
    await waitFor(() => expect(screen.getByTestId("connectors-error")).toBeInTheDocument());
    expect(screen.getByTestId("connectors-error")).toHaveTextContent("boom");
  });
});
