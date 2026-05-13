import { test, expect } from "@playwright/test";

// End-to-end smoke for the SESSION 116 auth slice. Drives the same
// pipeline `python manage.py smoke_headless_auth` exercises on the
// backend, but through a real browser hitting the SPA:
//
//   /sign-up → fill form → submit → /dashboard renders authenticated
//
// Backend must be running:
//   - Django runserver on :8000
//   - (Redis + media-engine optional; auth doesn't need them)
//
// The test creates a fresh email per run so re-runs don't collide.
// Cleanup runs in afterEach via a tiny admin-only DELETE endpoint we
// don't have yet, so for now the test leaves rows behind (operator
// can clean via Django admin). Adding a cleanup endpoint is a queued
// follow-up — flagged in SPA_ARCHITECTURE.md §"Smoke test pattern".

test.describe("auth flow (sign-up + sign-in forms)", () => {
  // The signup → dashboard happy path lives in `dashboard.spec.ts`
  // now that the dashboard has real content to assert on. This file
  // covers auth-specific behaviour: redirect on success + error UX.

  test("a fresh signup redirects to /dashboard", async ({ page }) => {
    const email = `e2e-auth-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await expect(page.getByRole("button", { name: /create account/i })).toBeVisible();

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);

    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("sign-in route shows a useful error on bad credentials", async ({ page }) => {
    await page.goto("/sign-in");
    await page.getByLabel("Email").fill("does-not-exist@character-os.test");
    await page.getByLabel("Password").fill("wrong-password-x4q9z");
    await page.getByRole("button", { name: /^sign in/i }).click();

    // We expect either a 400-class allauth error or a generic
    // failure copy. Either way, we should still be on /sign-in.
    // allauth ships "The email address and/or password you specified
    // are not correct." — match the structurally interesting words
    // across copies.
    await expect(page).toHaveURL(/\/sign-in/);
    await expect(
      page.getByText(/invalid|wrong|incorrect|not correct|request failed/i),
    ).toBeVisible();
  });
});
