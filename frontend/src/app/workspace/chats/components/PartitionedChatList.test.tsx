import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { PartitionedChatList } from "./PartitionedChatList";

const CHATS = [
  { id: "c1", title: "Manual 1", source: "manual" as const, updatedAt: "" },
  { id: "c2", title: "Auto 1", source: "automation" as const, updatedAt: "" },
  { id: "c3", title: "Channel 1", source: "channel" as const, updatedAt: "" },
];

describe("PartitionedChatList", () => {
  afterEach(() => cleanup());

  it("renders all threads by default", () => {
    render(<PartitionedChatList chats={CHATS} />);
    expect(screen.getByText("Manual 1")).toBeInTheDocument();
    expect(screen.getByText("Auto 1")).toBeInTheDocument();
    expect(screen.getByText("Channel 1")).toBeInTheDocument();
  });

  it("filters by automation when automation tab clicked", () => {
    render(<PartitionedChatList chats={CHATS} />);
    fireEvent.click(screen.getByTestId("tab-automation"));
    expect(screen.getByText("Auto 1")).toBeInTheDocument();
    expect(screen.queryByText("Manual 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Channel 1")).not.toBeInTheDocument();
  });

  it("filters by channel when channel tab clicked", () => {
    render(<PartitionedChatList chats={CHATS} />);
    fireEvent.click(screen.getByTestId("tab-channel"));
    expect(screen.getByText("Channel 1")).toBeInTheDocument();
    expect(screen.queryByText("Auto 1")).not.toBeInTheDocument();
  });

  it("switches back to all when 'All' tab clicked", () => {
    render(<PartitionedChatList chats={CHATS} />);
    fireEvent.click(screen.getByTestId("tab-manual"));
    expect(screen.queryByText("Auto 1")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("tab-all"));
    expect(screen.getByText("Auto 1")).toBeInTheDocument();
  });

  it("shows empty state when a partition has no chats", () => {
    render(<PartitionedChatList chats={[]} />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
  });

  it("marks the active tab with aria-selected", () => {
    render(<PartitionedChatList chats={CHATS} />);
    const allTab = screen.getByTestId("tab-all");
    expect(allTab.getAttribute("aria-selected")).toBe("true");
    fireEvent.click(screen.getByTestId("tab-manual"));
    expect(screen.getByTestId("tab-manual").getAttribute("aria-selected")).toBe("true");
    expect(allTab.getAttribute("aria-selected")).toBe("false");
  });
});
