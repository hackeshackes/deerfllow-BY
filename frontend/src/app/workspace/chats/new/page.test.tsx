import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import NewChatPage from "./page";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: vi.fn() }),
}));

vi.mock("@/core/i18n/hooks", () => ({
  useI18n: () => ({
    t: {
      chats: {
        newChatTitle: "Start a new chat",
        newChatSubtitle: "Pick a scene to begin",
        start: "Start",
      },
      common: { cancel: "Cancel" },
    },
  }),
}));

describe("NewChatPage", () => {
  afterEach(() => {
    cleanup();
    pushMock.mockReset();
    window.localStorage.clear();
  });

  it("renders the scene selector and start button", () => {
    render(<NewChatPage />);
    expect(screen.getByTestId("new-chat-page")).toBeInTheDocument();
    expect(screen.getByTestId("scene-selector")).toBeInTheDocument();
    expect(screen.getByTestId("start-chat")).toBeInTheDocument();
  });

  it("persists the chosen scene to localStorage and navigates", () => {
    render(<NewChatPage />);
    fireEvent.click(screen.getByTestId("scene-qa"));
    fireEvent.click(screen.getByTestId("start-chat"));
    expect(window.localStorage.getItem("micx_pending_scene")).toBe("qa");
    expect(pushMock).toHaveBeenCalledWith("/workspace");
  });

  it("navigates back to the chat list on cancel", () => {
    render(<NewChatPage />);
    fireEvent.click(screen.getByTestId("start-chat").previousElementSibling as HTMLElement);
    expect(pushMock).toHaveBeenCalledWith("/workspace/chats");
  });
});
