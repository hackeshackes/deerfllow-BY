import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  update: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "w1" }),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/workspace/workflows/w1/edit",
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/components/brand/brand-provider", () => ({
  useBrand: () => ({
    name: "MicX",
    shortName: "MIcX",
    tagline: "tagline",
    description: "desc",
  }),
}));

vi.mock("@/core/canvas/api", () => ({
  canvasApi: {
    get: mocks.get,
    list: vi.fn(),
    create: vi.fn(),
    update: mocks.update,
    remove: vi.fn(),
    listVersions: vi.fn(),
    rollback: vi.fn(),
    execute: vi.fn(),
  },
}));

vi.mock("@/core/spaces/hooks/use-current-space", () => ({
  useCurrentSpace: () => ({ space: { id: "ws-1", name: "Personal" }, isLoading: false, error: null }),
}));

vi.mock("@/core/i18n/hooks", () => ({
  useI18n: () => ({
    t: {
      canvasWorkflows: {
        editTitle: "Edit",
        backToList: "Back",
        saveChanges: "Save",
        savingChanges: "Saving",
        savedAt: "Saved at {time}",
        common: { loading: "Loading..." },
      },
      common: { loading: "Loading...", home: "Home" },
      breadcrumb: { workspace: "Workspace" },
      workspace: { about: "About" },
    },
  }),
}));

import EditWorkflowPage from "./page";

afterEach(() => cleanup());
beforeEach(() => {
  mocks.get.mockReset();
  mocks.update.mockReset();
});

describe("EditWorkflowPage", () => {
  it("adds a node when palette is clicked", async () => {
    mocks.get.mockResolvedValueOnce({
      id: "w1",
      name: "Demo",
      workspace_id: "ws-1",
      status: "draft",
      version: 1,
      nodes: [],
      edges: [],
      created_at: "t",
      updated_at: "t",
    });

    render(<EditWorkflowPage />);

    await waitFor(() => {
      expect(screen.getByTestId("workflow-edit-name")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("palette-prompt"));
    expect(screen.getByTestId(/^node-n-prompt-/)).toBeInTheDocument();
  });

  it("calls update on save", async () => {
    mocks.get.mockResolvedValueOnce({
      id: "w1",
      name: "Demo",
      workspace_id: "ws-1",
      status: "draft",
      version: 1,
      nodes: [],
      edges: [],
      created_at: "t",
      updated_at: "t",
    });
    mocks.update.mockResolvedValueOnce({ id: "w1", updated_at: "2026-07-01T00:00:00Z" });

    render(<EditWorkflowPage />);

    await waitFor(() => {
      expect(screen.getByTestId("workflow-edit-save")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("palette-tool"));
    fireEvent.click(screen.getByTestId("workflow-edit-save"));

    await waitFor(() => {
      expect(mocks.update).toHaveBeenCalledWith("w1", expect.objectContaining({ nodes: expect.any(Array) }));
    });
  });
});
