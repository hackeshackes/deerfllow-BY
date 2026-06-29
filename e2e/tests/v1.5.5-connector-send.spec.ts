/**
 * v1.5.5 end-to-end smoke.
 *
 * Prerequisites:
 *   - Gateway running on http://localhost:2026 (via `make dev`)
 *   - Playwright browsers installed
 *   - The e2e test user has been provisioned in the workspace
 *
 * Run with: `cd e2e && pnpm test v1.5.5-connector-send.spec.ts`
 *
 * These tests are skipped in CI when the env var `E2E_LIVE=1` is not set —
 * the spec is the executable description, not a CI gate.
 */
import { test, expect } from "@playwright/test";

const E2E_LIVE = process.env.E2E_LIVE === "1";
const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:2026";

test.describe("v1.5.5 connector + workspace", () => {
  test.skip(!E2E_LIVE, "Set E2E_LIVE=1 to run live e2e tests");

  test("connector list is visible in admin", async ({ page }) => {
    await page.goto(`${BASE_URL}/sign-in`);
    await page.fill('input[name=email]', "admin@example.com");
    await page.fill('input[name=password]', "test-password-1234");
    await page.click('button[type=submit]');
    await page.goto(`${BASE_URL}/workspace/admin/connectors`);
    await expect(page.getByText("Feishu")).toBeVisible();
    await expect(page.getByText("DingTalk")).toBeVisible();
    await expect(page.getByText("WeCom")).toBeVisible();
    await expect(page.getByText("Email")).toBeVisible();
  });

  test("workspace switcher visible in sidebar", async ({ page }) => {
    // Assumes storageState with an active session.
    await page.goto(`${BASE_URL}/workspace`);
    await expect(page.getByTestId("workspace-switcher")).toBeVisible();
  });
});
