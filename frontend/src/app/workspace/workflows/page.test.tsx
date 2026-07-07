import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkflows } from "@/core/canvas/hooks/use-workflows";
import { useCurrentSpace } from "@/core/spaces/hooks/use-current-space";

vi.mock("@/core/spaces/hooks/use-current-space", () => ({
  useCurrentSpace: vi.fn(),
}));

vi.mock("@/core/canvas/hooks/use-workflows", () => ({
  useWorkflows: vi.fn(),
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

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/workspace/workflows",
}));

vi.mock("@/core/i18n/hooks", () => ({
  useI18n: () => ({
    t: {
      canvasWorkflows: {
        listTitle: "Workflows",
        listDescription: "desc",
        newWorkflow: "New",
        emptyTitle: "No workflows yet",
        emptyDescription: "empty",
        createButton: "Create",
        errorTitle: "Error",
        versionLabel: "v",
        common: { loading: "Loading..." },
      },
      common: { loading: "Loading...", edit: "Edit", home: "Home" },
      breadcrumb: { workspace: "Workspace" },
      workspace: { about: "About" },
    },
  }),
}));

const mockedUseCurrentSpace = vi.mocked(useCurrentSpace);
const mockedUseWorkflows = vi.mocked(useWorkflows);

import WorkflowsListPage from "./page";

afterEach(() => cleanup());

beforeEach(() => {
  vi.clearAllMocks();
});

describe("WorkflowsListPage", () => {
  it("shows the empty state when there are no workflows", async () => {
    mockedUseCurrentSpace.mockReturnValue({ space: { id: "ws-1", name: "Personal", type: "personal" }, isLoading: false, error: null });
    mockedUseWorkflows.mockReturnValue({
      workflows: [],
      isLoading: false,
      error: null,
      refresh: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
    });

    render(<WorkflowsListPage />);

    await waitFor(() => {
      expect(screen.getByTestId("workflows-empty")).toBeInTheDocument();
    });
    expect(screen.getByText("No workflows yet")).toBeInTheDocument();
  });

  it("renders a card per workflow", async () => {
    mockedUseCurrentSpace.mockReturnValue({ space: { id: "ws-1", name: "Personal", type: "personal" }, isLoading: false, error: null });
    mockedUseWorkflows.mockReturnValue({
      workflows: [
        {
          id: "w1",
          name: "Demo",
          workspace_id: "ws-1",
          status: "draft",
          version: 2,
          nodes: [{ id: "n1", kind: "prompt", config: {}, position: [0, 0] }],
          edges: [],
          created_at: "2026-07-01T00:00:00Z",
          updated_at: "2026-07-02T00:00:00Z",
        },
      ],
      isLoading: false,
      error: null,
      refresh: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
    });

    render(<WorkflowsListPage />);

    await waitFor(() => {
      expect(screen.getByTestId("workflow-card")).toBeInTheDocument();
    });
    expect(screen.getByText("Demo")).toBeInTheDocument();
  });

  it("shows an error banner when load fails", async () => {
    mockedUseCurrentSpace.mockReturnValue({ space: { id: "ws-1", name: "Personal", type: "personal" }, isLoading: false, error: null });
    mockedUseWorkflows.mockReturnValue({
      workflows: [],
      isLoading: false,
      error: new Error("boom"),
      refresh: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
    });

    render(<WorkflowsListPage />);

    await waitFor(() => {
      expect(screen.getByTestId("workflows-error")).toBeInTheDocument();
    });
  });
});
