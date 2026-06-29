import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PartitionedChatList } from "@/app/workspace/chats/components/PartitionedChatList";
import { WorkspaceSwitcher } from "@/app/workspace/components/WorkspaceSwitcher";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

vi.mock("@/core/spaces/hooks/use-spaces", () => ({
  useSpaces: () => ({
    spaces: [
      { id: "personal", name: "Personal", type: "personal" },
      { id: "ws-engineering", name: "Engineering", type: "workspace" },
    ],
    isLoading: false,
  }),
}));

describe("spaces + chat list integration", () => {
  afterEach(() => {
    cleanup();
    document.cookie = "micx_space=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
  });

  it("renders the switcher and partitioned chat list side-by-side", () => {
    render(
      <div>
        <WorkspaceSwitcher />
        <PartitionedChatList
          chats={[
            { id: "c1", title: "Draft spec", source: "manual", updatedAt: "" },
            { id: "c2", title: "Daily standup", source: "automation", updatedAt: "" },
            { id: "c3", title: "Feishu thread", source: "channel", updatedAt: "" },
          ]}
        />
      </div>,
    );

    // Switcher is present and lists both spaces
    const switcher = screen.getByTestId("workspace-switcher") as HTMLSelectElement;
    expect(switcher).toBeInTheDocument();
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(screen.getByText("Engineering")).toBeInTheDocument();

    // Partitioned list shows all chats by default
    expect(screen.getByTestId("partitioned-chat-list")).toBeInTheDocument();
    expect(screen.getByText("Draft spec")).toBeInTheDocument();
    expect(screen.getByText("Daily standup")).toBeInTheDocument();
    expect(screen.getByText("Feishu thread")).toBeInTheDocument();
  });
});
