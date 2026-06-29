import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

vi.mock("@/core/spaces/hooks/use-spaces", () => ({
  useSpaces: () => ({
    spaces: [
      { id: "personal", name: "Personal", type: "personal" },
      { id: "ws-product", name: "Product Team", type: "workspace" },
    ],
    isLoading: false,
  }),
}));

function clearSpaceCookie() {
  document.cookie = `micx_space=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

describe("WorkspaceSwitcher", () => {
  beforeEach(() => clearSpaceCookie());
  afterEach(() => {
    cleanup();
    clearSpaceCookie();
  });

  it("renders all spaces in the dropdown", () => {
    render(<WorkspaceSwitcher />);
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(screen.getByText("Product Team")).toBeInTheDocument();
  });

  it("defaults to personal when no currentSpaceId is given", () => {
    render(<WorkspaceSwitcher />);
    const select = screen.getByTestId("workspace-switcher") as HTMLSelectElement;
    expect(select.value).toBe("personal");
  });

  it("respects the currentSpaceId prop", () => {
    render(<WorkspaceSwitcher currentSpaceId="ws-product" />);
    const select = screen.getByTestId("workspace-switcher") as HTMLSelectElement;
    expect(select.value).toBe("ws-product");
  });

  it("sets the micx_space cookie on change", () => {
    render(<WorkspaceSwitcher />);
    const select = screen.getByTestId("workspace-switcher");
    fireEvent.change(select, { target: { value: "ws-product" } });
    expect(document.cookie).toContain("micx_space=ws-product");
  });
});
