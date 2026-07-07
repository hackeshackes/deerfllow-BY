import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  execute: vi.fn(),
  runHook: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "w1" }),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/workspace/workflows/w1",
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
    update: vi.fn(),
    remove: vi.fn(),
    listVersions: vi.fn(),
    rollback: vi.fn(),
    execute: mocks.execute,
  },
}));

vi.mock("@/core/canvas/hooks/use-workflow-execute", () => ({
  useWorkflowExecute: () => mocks.runHook(),
}));

vi.mock("@/core/spaces/hooks/use-current-space", () => ({
  useCurrentSpace: () => ({ space: { id: "ws-1", name: "Personal", type: "personal" }, isLoading: false, error: null }),
}));

vi.mock("@/core/i18n/hooks", () => ({
  useI18n: () => ({
    t: {
      canvasWorkflows: {
        backToList: "Back",
        detailTitle: "Detail",
        versionLabel: "v",
        run: "Run",
        running: "Running",
        runInputs: "Inputs",
        runError: "Run failed",
        quotaExceeded: "Quota exceeded",
        notFound: "Not found",
      },
      common: { loading: "Loading...", edit: "Edit", home: "Home" },
      breadcrumb: { workspace: "Workspace" },
      workspace: { about: "About" },
    },
  }),
}));

import WorkflowDetailPage from "./page";

afterEach(() => cleanup());
beforeEach(() => {
  mocks.get.mockReset();
  mocks.execute.mockReset();
  mocks.runHook.mockReset();
  mocks.runHook.mockReturnValue({
    isRunning: false,
    result: null,
    error: null,
    run: vi.fn(),
    reset: vi.fn(),
  });
});

describe("WorkflowDetailPage", () => {
  it("renders the workflow name on load", async () => {
    mocks.get.mockResolvedValueOnce({
      id: "w1",
      name: "Demo",
      workspace_id: "ws-1",
      status: "draft",
      version: 1,
      nodes: [],
      edges: [],
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    render(<WorkflowDetailPage />);

    await waitFor(() => {
      expect(screen.getByTestId("workflow-detail-name")).toHaveTextContent("Demo");
    });
  });

  it("surfaces the quota-exceeded i18n key on a 429 error", async () => {
    mocks.get.mockResolvedValueOnce({
      id: "w1",
      name: "Demo",
      workspace_id: "ws-1",
      status: "draft",
      version: 1,
      nodes: [],
      edges: [],
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });
    mocks.runHook.mockReturnValue({
      isRunning: false,
      result: null,
      error: new Error("canvas API 429: {\"error\":{\"code\":\"QUOTA_EXCEEDED\"}}"),
      run: vi.fn(),
      reset: vi.fn(),
    });

    render(<WorkflowDetailPage />);

    await waitFor(() => {
      expect(screen.getByTestId("workflow-run-error")).toHaveTextContent(/Quota exceeded/);
    });
  });
});
