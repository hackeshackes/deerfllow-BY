import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AuditPage from "./page";

vi.mock("@/core/identity/api", () => ({
  identityApi: {
    queryAudit: vi.fn().mockResolvedValue({
      events: [
        {
          id: "e1",
          occurred_at: "2026-06-22T00:00:00Z",
          actor_id: "u1",
          actor_type: "user",
          action: "thread.create",
          resource_type: "thread",
          resource_id: "t1",
          workspace_id: "w1",
          success: true,
          metadata: {},
        },
      ],
    }),
  },
}));

describe("AuditPage", () => {
  it("renders events", async () => {
    render(<AuditPage />);
    await waitFor(() => {
      expect(screen.getByText("thread.create")).toBeInTheDocument();
    });
  });
});