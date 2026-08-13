import { test, expect } from "@playwright/test";

// R8.0 / SESSION 153 — realtime "Talk to spokesperson" route.
//
// Minimal sanity check: the route is registered + the
// spokesperson-not-found path renders cleanly. The full
// session-create lifecycle (start → live → end) needs a
// configured spokesperson with runway_avatar_id seeded,
// which the wizard-driven flow doesn't expose cleanly to
// e2e. R8.1 will add a seeded-fixture spec; for now this
// guards against route-registration regressions.

test.describe("realtime talk route (R8.0)", () => {
  test("404 path renders fatal error state", async ({ page }) => {
    const email = `e2e-r8-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    const fakeId = "11111111-1111-1111-1111-111111111111";
    await page.goto(`/spokespeople/${fakeId}/talk`);
    // Spokesperson not found surfaces as the fatal-error
    // panel (TalkError component).
    await expect(page.getByTestId("talk-fatal-error")).toBeVisible();
  });
});
