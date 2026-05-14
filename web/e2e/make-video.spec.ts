import { test, expect } from "@playwright/test";

// SESSION 121 — full S-12 + S-11 lifecycle end-to-end:
//   signup → create spokesperson with portrait → "Make a video"
//   → fill brief → submit → land on /videos/{id} → polling page
//   → mock render lands ready in ~13s → <video> element visible.
//
// Backend deps: Django :8000 + Redis :6381 + Celery worker
// (`celery -A character_os worker --pool=solo`) + media-engine :8001
// all running. The polling test is the only spec that needs the
// Celery worker.

const SILENT_PNG_BUFFER = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
  "base64",
);

test.describe("make-a-video lifecycle (S-12 + S-11)", () => {
  test.setTimeout(60_000); // mock render takes ~13s; allow generous headroom

  test("fresh signup → create spokesperson → render → playback", async ({ page }) => {
    const email = `e2e-make-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    // 1) Sign up
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    // 2) Create spokesperson with portrait (avatar binds in mock mode).
    //    Uses the legacy single-form (?legacy=1) — faster than the
    //    4-step wizard for this make-video-focused lifecycle test.
    await page.goto("/spokespeople/new?legacy=1");
    await page.getByLabel("Name").fill("Render Test Spokesperson");
    await page
      .getByLabel("Business brief")
      .fill("Sells artisan bicycle bells. Warm, opinionated.");
    await page.getByTestId("portrait-input").setInputFiles({
      name: "test.png",
      mimeType: "image/png",
      buffer: SILENT_PNG_BUFFER,
    });

    await Promise.all([
      page.waitForURL(/\/spokespeople\/[0-9a-f-]+$/),
      page.getByTestId("create-submit").click(),
    ]);

    // 3) Detail page — "Make a video" should be enabled (avatar
    //    bound via the portrait → mock avatar id pipeline).
    const makeVideoLink = page.getByTestId("make-video-link");
    await expect(makeVideoLink).toBeVisible();
    await expect(makeVideoLink.getByRole("button")).toBeEnabled();

    await Promise.all([
      page.waitForURL(/\/spokespeople\/[0-9a-f-]+\/render$/),
      makeVideoLink.click(),
    ]);

    // 4) Render form — brief should be pre-filled from the
    //    spokesperson's business_brief.
    await expect(page.getByText(/Make a video/i)).toBeVisible();
    const brief = page.getByLabel("Brief");
    await expect(brief).toHaveValue(/artisan bicycle bells/i);

    // 5) Customize per-video + submit
    await page.getByLabel("Title").fill("Black Friday spot");
    await brief.fill("Black Friday bell sale — 30% off. Just this week.");

    await Promise.all([
      page.waitForURL(/\/videos\/[0-9a-f-]+$/),
      page.getByTestId("render-submit").click(),
    ]);

    // 6) Status page — pending or rendering initially. Title +
    //    masthead + status pill visible.
    await expect(page.getByTestId("video-masthead")).toBeVisible();
    await expect(page.getByTestId("video-title")).toContainText(
      /black friday spot/i,
    );
    const statusPill = page.getByTestId("status-pill");
    await expect(statusPill).toBeVisible();

    // 7) Wait for the Celery worker to flip the row to ready. Mock
    //    mode takes ~13s. The polling hook re-fetches every 2s and
    //    halts on terminal — the playback panel mounts at that
    //    point.
    await expect(statusPill).toHaveText(/ready/i, { timeout: 45_000 });
    const player = page.getByTestId("video-player");
    await expect(player).toBeVisible();
    await expect(player).toHaveAttribute("src", /https?:\/\//);

    // 8) Going back to /dashboard should now show the row in
    //    Recent renders. Click into it from the dashboard list.
    await page.goto("/dashboard");
    const row = page.getByTestId("video-row").first();
    await expect(row).toBeVisible();
    await expect(row).toContainText(/black friday spot/i);

    await Promise.all([
      page.waitForURL(/\/videos\/[0-9a-f-]+$/),
      row.getByRole("link", { name: /black friday spot/i }).click(),
    ]);
    // Same row we came from — playback panel still there.
    await expect(page.getByTestId("video-player")).toBeVisible();
  });
});
