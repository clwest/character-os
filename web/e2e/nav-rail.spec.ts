import { test, expect } from "@playwright/test";

// SESSION 144 / F2 — persistent nav rail.
//
// The rail mounts only on authenticated, non-auth routes.
// It exposes four sections (Dashboard, Spokespeople,
// Knowledge, Recipes) and highlights the active one by
// pathname prefix.
//
// F0 contract rule 7 — adding a fifth top-level section
// requires its own scope-lock event. The hard count below
// is a regression net.

test.describe("nav rail (F2)", () => {
  test("hidden on auth routes", async ({ page }) => {
    await page.goto("/sign-up");
    await expect(page.getByTestId("nav-rail")).not.toBeVisible();
    await page.goto("/sign-in");
    await expect(page.getByTestId("nav-rail")).not.toBeVisible();
  });

  test("renders four sections on the dashboard", async ({ page }) => {
    const email = `e2e-rail-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    const rail = page.getByTestId("nav-rail");
    await expect(rail).toBeVisible();
    await expect(page.getByTestId("nav-dashboard")).toBeVisible();
    await expect(page.getByTestId("nav-spokespeople")).toBeVisible();
    await expect(page.getByTestId("nav-knowledge")).toBeVisible();
    await expect(page.getByTestId("nav-recipes")).toBeVisible();

    // Hard count — F0 contract rule 7 protects against an
    // accidental fifth section sneaking in.
    const items = rail.locator("[data-testid^='nav-']");
    await expect(items).toHaveCount(4);

    // Active section is dashboard.
    await expect(page.getByTestId("nav-dashboard")).toHaveAttribute(
      "data-active",
      "true",
    );
  });

  test("clicking Recipes activates the recipes section", async ({ page }) => {
    const email = `e2e-rail2-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.waitForURL("**/dashboard");

    await Promise.all([
      page.waitForURL("**/recipes"),
      page.getByTestId("nav-recipes").click(),
    ]);

    await expect(page.getByTestId("nav-recipes")).toHaveAttribute(
      "data-active",
      "true",
    );
    await expect(page.getByTestId("nav-dashboard")).toHaveAttribute(
      "data-active",
      "false",
    );
  });
});
