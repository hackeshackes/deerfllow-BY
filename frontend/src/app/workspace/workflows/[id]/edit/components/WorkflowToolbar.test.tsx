import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  listVersions: vi.fn(),
  rollback: vi.fn(),
}));

vi.mock("@/core/canvas/hooks/use-workflow-versions", () => ({
  useWorkflowVersions: () => ({
    versions: [
      { workflow_id: "w1", version: 1, created_at: "2026-07-01T00:00:00Z", snapshot: {} as never },
      { workflow_id: "w1", version: 2, created_at: "2026-07-02T00:00:00Z", snapshot: {} as never },
    ],
    isLoading: false,
    error: null,
    refresh: vi.fn(),
    rollback: mocks.rollback,
  }),
}));

vi.mock("@/components/brand/brand-provider", () => ({
  useBrand: () => ({ name: "MicX", shortName: "MIcX" }),
}));

vi.mock("@/core/i18n/hooks", () => ({
  useI18n: () => ({
    t: {
      canvasWorkflows: { versionLabel: "v" },
      common: { loading: "Loading..." },
    },
  }),
}));

import { WorkflowToolbar } from "./WorkflowToolbar";

afterEach(() => cleanup());
beforeEach(() => {
  mocks.rollback.mockReset();
});

describe("WorkflowToolbar", () => {
  it("renders the current version label", () => {
    render(<WorkflowToolbar workflowId="w1" currentVersion={2} />);
    expect(screen.getByTestId("toolbar-history")).toHaveTextContent(/v\s*2/);
  });

  it("opens the version dropdown on click", () => {
    render(<WorkflowToolbar workflowId="w1" currentVersion={2} />);
    fireEvent.click(screen.getByTestId("toolbar-history"));
    expect(screen.getByTestId("toolbar-versions")).toBeInTheDocument();
  });

  it("calls onRollback when a non-current version's button is clicked", async () => {
    const onRollback = vi.fn();
    render(<WorkflowToolbar workflowId="w1" currentVersion={2} onRollback={onRollback} />);
    fireEvent.click(screen.getByTestId("toolbar-history"));
    fireEvent.click(screen.getByTestId("toolbar-rollback-1"));
    await waitFor(() => {
      expect(onRollback).toHaveBeenCalledWith(1);
    });
  });

  it("does not show a rollback button for the current version", () => {
    render(<WorkflowToolbar workflowId="w1" currentVersion={2} />);
    fireEvent.click(screen.getByTestId("toolbar-history"));
    expect(screen.queryByTestId("toolbar-rollback-2")).not.toBeInTheDocument();
    expect(screen.getByTestId("toolbar-rollback-1")).toBeInTheDocument();
  });

  it("renders a no-workflow placeholder when workflowId is null", () => {
    render(<WorkflowToolbar workflowId={null} currentVersion={0} />);
    const root = screen.getByTestId("workflow-toolbar");
    expect(root.getAttribute("data-disabled")).toBe("no-workflow");
  });
});
