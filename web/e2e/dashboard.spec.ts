import { test, expect } from "@playwright/test";

// SESSION 117 Slice 2 e2e. Drives the dashboard's "fresh signup →
// empty state" flow:
//   1. New user signs up
//   2. RequireAuth lets them through
//   3. Dashboard masthead shows their auto-created workspace name
//   4. Spokespeople panel renders the empty state
//   5. Recent renders panel renders the empty state
//   6. Usage meter shows "0 / 10 starter trialing"
//
// Same backend dependencies as auth.spec.ts (Django :8000 up).

test.describe("workspace dashboard (S-09)", () => {
  test("a fresh signup lands on a populated empty-state dashboard", async ({ page }) => {
    const email = `e2e-dash-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    // 1) Sign up (same as auth.spec.ts's happy path)
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    // 2) Masthead — workspace name + sign-out + signed-in email
    const masthead = page.getByTestId("dashboard-masthead");
    await expect(masthead).toBeVisible();
    // Workspace name auto-derives from the email prefix; the prefix
    // starts "e2e-dash-..." so the rendered name should contain it.
    await expect(page.getByTestId("workspace-name")).toContainText(/e2e-dash-/i);
    await expect(page.getByTestId("sign-out")).toBeVisible();

    // 3) Primary action panel renders the headline copy
    const primary = page.getByTestId("primary-action");
    await expect(primary).toContainText(/type your business/i);
    await expect(primary.getByRole("button", { name: /make a video/i })).toBeVisible();

    // 4) Spokespeople empty state — fresh workspace has none
    await expect(page.getByTestId("spokespeople-empty")).toBeVisible();
    await expect(page.getByTestId("spokespeople-empty")).toContainText(
      /no spokespeople yet/i,
    );

    // 5) Recent renders empty state
    await expect(page.getByTestId("videos-empty")).toBeVisible();
    await expect(page.getByTestId("videos-empty")).toContainText(/no renders yet/i);

    // 6) Usage meter — should render "0 / 10" on Starter trialing
    await expect(page.getByText(/^0\s*\/\s*10$/)).toBeVisible();
    await expect(page.getByText(/^Starter$/i)).toBeVisible();
    await expect(page.getByText(/^Trialing$/i)).toBeVisible();
  });

  test("sign out returns the user to /sign-in", async ({ page }) => {
    const email = `e2e-dash-out-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    await Promise.all([
      page.waitForURL("**/sign-in"),
      page.getByTestId("sign-out").click(),
    ]);
    await expect(page).toHaveURL(/\/sign-in/);

    // Hitting a protected route should redirect back to /sign-in
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/sign-in/);
  });
});
