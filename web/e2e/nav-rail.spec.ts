import { test, expect } from "@playwright/test";

// SESSION 144 / F2 — persistent nav rail.
//
// The rail mounts only on authenticated, non-auth routes.
// Expanded SESSION 209 to 11 sections to surface the post-F-arc
// workspace additions (Transcripts, Scripts, Campaigns, Bundles,
// Videos, Assets). Each new entry is authorized by its own
// scope-lock doc (TRANSCRIPT_MINER_V1, AUTO_SCRIPTING_V1,
// PERSONALIZED_VIDEO_V1, PUBLISH_BUNDLE_V1, ASSET_LIBRARY_V1) —
// F0 contract rule 7 satisfied. Videos is the paginated
// composition library shipped SESSION 209 Path A.

test.describe("nav rail (F2)", () => {
  test("hidden on auth routes", async ({ page }) => {
    await page.goto("/sign-up");
    await expect(page.getByTestId("nav-rail")).not.toBeVisible();
    await page.goto("/sign-in");
    await expect(page.getByTestId("nav-rail")).not.toBeVisible();
  });

  test("renders eleven sections on the dashboard", async ({ page }) => {
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
    await expect(page.getByTestId("nav-transcripts")).toBeVisible();
    await expect(page.getByTestId("nav-scripts")).toBeVisible();
    await expect(page.getByTestId("nav-recipes")).toBeVisible();
    await expect(page.getByTestId("nav-campaigns")).toBeVisible();
    await expect(page.getByTestId("nav-bundles")).toBeVisible();
    await expect(page.getByTestId("nav-videos")).toBeVisible();
    await expect(page.getByTestId("nav-assets")).toBeVisible();
    await expect(page.getByTestId("nav-images")).toBeVisible();

    // Hard count — guards against accidental drift between rail
    // entries and the scope-locked surfaces they expose.
    const items = rail.locator("[data-testid^='nav-']");
    await expect(items).toHaveCount(11);

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
