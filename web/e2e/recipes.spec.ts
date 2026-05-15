import { test, expect } from "@playwright/test";

// SESSION 144 / V15.4 — recipe gallery e2e spec.
//
// Replaces the legacy ``make-video.spec.ts`` which tested the
// pre-V15 single-form render flow at /spokespeople/:id/render
// (retired SESSION 144). The new flow:
//
//   1. Sign up → workspace auto-created
//   2. Dashboard "Make a video" CTA → /recipes
//   3. Gallery shows 18 recipe cards grouped by family
//   4. Live recipes are clickable; coming-soon cards are not in
//      v1 — actually all 18 are live as of V15.4 (no coming-soon
//      labels), so we only assert at the card-count level.
//   5. Clicking a recipe opens the form; cancel returns to
//      the gallery.
//
// We don't exercise full composition submission here because
// it requires a spokesperson + avatar binding (the
// make-video.spec.ts setup was 5 minutes long). Submission is
// covered by backend tests in test_v15_api.py
// (test_create_talking_head_composition_runs_end_to_end et al).

test.describe("recipe gallery (V15.4)", () => {
  test("dashboard CTA leads to the gallery", async ({ page }) => {
    const email = `e2e-rcp-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    await Promise.all([
      page.waitForURL("**/recipes"),
      page.getByTestId("make-video-cta").click(),
    ]);

    await expect(
      page.getByRole("heading", { name: /pick a recipe/i }),
    ).toBeVisible();

    // 18 recipe cards (V15.4 final count: 17 from starters.py +
    // storyboard_voiced bonus). Hard count protects against
    // regression if a recipe accidentally falls out of the
    // registry.
    const cards = page.locator('[data-testid^="recipe-card-"]');
    await expect(cards).toHaveCount(18);
  });

  test("opening a live recipe shows its form", async ({ page }) => {
    const email = `e2e-rcp2-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.waitForURL("**/dashboard");

    await page.goto("/recipes/talking_head");

    await expect(
      page.getByRole("heading", { name: /talking head/i }),
    ).toBeVisible();
    await expect(page.getByTestId("recipe-form-talking_head")).toBeVisible();
    await expect(page.getByTestId("recipe-field-spokesperson_id")).toBeVisible();
    await expect(page.getByTestId("recipe-field-script")).toBeVisible();
  });
});
