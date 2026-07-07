import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const create = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useParams: () => ({}),
  usePathname: () => "/workspace/workflows/new",
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

vi.mock("@/core/spaces/hooks/use-current-space", () => ({
  useCurrentSpace: () => ({ space: { id: "ws-1", name: "Personal" }, isLoading: false, error: null }),
}));

vi.mock("@/core/canvas/hooks/use-workflows", () => ({
  useWorkflows: () => ({
    workflows: [],
    isLoading: false,
    error: null,
    refresh: vi.fn(),
    create,
    update: vi.fn(),
    remove: vi.fn(),
  }),
}));

vi.mock("@/core/i18n/hooks", () => ({
  useI18n: () => ({
    t: {
      canvasWorkflows: {
        createTitle: "New workflow",
        createDescription: "desc",
        nameLabel: "Name",
        namePlaceholder: "My workflow",
        workspaceLabel: "Workspace",
        createSubmit: "Create",
        createCancel: "Cancel",
        createError: "Failed",
        backToList: "Back",
      },
      common: { loading: "Loading...", home: "Home" },
      breadcrumb: { workspace: "Workspace" },
      workspace: { about: "About" },
    },
  }),
}));

import NewWorkflowPage from "./page";

afterEach(() => cleanup());
beforeEach(() => {
  push.mockReset();
  create.mockReset();
});

describe("NewWorkflowPage", () => {
  it("submits and navigates to /edit on success", async () => {
    create.mockResolvedValueOnce({ id: "w-new", name: "fresh", version: 1 });
    render(<NewWorkflowPage />);

    const nameInput = screen.getByTestId("workflow-name-input");
    fireEvent.change(nameInput, { target: { value: "fresh" } });
    fireEvent.click(screen.getByTestId("workflow-new-submit"));

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith("/workspace/workflows/w-new/edit");
    });
  });

  it("shows error when create fails", async () => {
    create.mockRejectedValueOnce(new Error("denied"));
    render(<NewWorkflowPage />);

    fireEvent.change(screen.getByTestId("workflow-name-input"), { target: { value: "fresh" } });
    fireEvent.click(screen.getByTestId("workflow-new-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("workflow-new-error")).toBeInTheDocument();
    });
    expect(push).not.toHaveBeenCalled();
  });
});
