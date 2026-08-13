import { test, expect } from "@playwright/test";

// SESSION 144 / F8 — onboarding tour banner.
//
// Fresh signup lands on dashboard → tour banner visible at
// step 1 ("Create your first spokesperson"). Dismissing
// persists across reloads via localStorage.
//
// The tour state derives from workspace data (no stored
// step progress), so completing a step naturally advances
// the banner. We don't exercise that here — the per-step
// content is verified at step 1 + the dismiss behavior is
// the load-bearing UX contract.

test.describe("onboarding tour (F8)", () => {
  test("fresh signup sees step 1; dismiss persists across reload", async ({ page }) => {
    const email = `e2e-tour-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    // Step 1 — "Create your first spokesperson"
    const tour = page.getByTestId("onboarding-tour");
    await expect(tour).toBeVisible();
    await expect(tour).toContainText(/step 1 of 3/i);
    await expect(tour).toContainText(/create your first spokesperson/i);
    await expect(page.getByTestId("tour-step-spokesperson")).toBeVisible();

    // Dismiss → banner hidden
    await page.getByTestId("onboarding-tour-dismiss").click();
    await expect(tour).not.toBeVisible();

    // Reload → still hidden (localStorage persists)
    await page.reload();
    await expect(page.getByTestId("dashboard-masthead")).toBeVisible();
    await expect(page.getByTestId("onboarding-tour")).not.toBeVisible();
  });

  test("step CTA links to the wizard route", async ({ page }) => {
    const email = `e2e-tour-cta-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.waitForURL("**/dashboard");

    await Promise.all([
      page.waitForURL("**/spokespeople/new"),
      page.getByTestId("tour-step-spokesperson").click(),
    ]);
    await expect(page).toHaveURL(/\/spokespeople\/new/);
  });
});
