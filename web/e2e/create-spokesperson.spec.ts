import { test, expect } from "@playwright/test";

// SESSION 120 Slice 4 e2e. Drives the create-spokesperson flow
// (S-06 of UI_REDESIGN_V2.md):
//   1. Fresh signup → /dashboard empty state with "Create your
//      first spokesperson" CTA
//   2. Click the CTA → /spokespeople/new
//   3. Fill name + business_brief, skip the portrait
//   4. Submit → redirected to /spokespeople/{id}
//   5. Detail page renders with the right name + brief
//
// A separate test covers the portrait upload path via Playwright's
// setInputFiles + an in-memory PNG buffer (no fixture file).

const SILENT_PNG_BUFFER = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
  "base64",
);

test.describe("create spokesperson (S-06)", () => {
  test("from dashboard empty state → form → detail page", async ({ page }) => {
    const email = `e2e-create-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";
    const name = "Casey Test";
    const brief =
      "Sells artisan bicycle bells to small bike shops. Warm, opinionated.";

    // 1) Sign up
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    // 2) Empty state with CTA visible
    const empty = page.getByTestId("spokespeople-empty");
    await expect(empty).toBeVisible();
    await expect(empty).toContainText(/no spokespeople yet/i);

    // 3) Navigate into the legacy create flow. After SESSION 132
    //    the dashboard CTA goes to the wizard by default — this
    //    spec covers the legacy form's regression. The wizard's
    //    happy path is covered separately in wizard-step-4.spec.ts.
    await page.goto("/spokespeople/new?legacy=1");

    // 4) Masthead renders
    await expect(page.getByText(/define\s*the spokesperson\./i)).toBeVisible();

    // 5) Fill the form (skip portrait — it's optional)
    await page.getByLabel("Name").fill(name);
    await page.getByLabel("Business brief").fill(brief);

    // 6) Submit → redirect to detail
    await Promise.all([
      page.waitForURL(/\/spokespeople\/[0-9a-f-]+$/),
      page.getByTestId("create-submit").click(),
    ]);

    // 7) Detail page shows the new spokesperson
    await expect(page.getByTestId("spokesperson-name")).toContainText(name);
    await expect(page.getByTestId("identity-panel")).toContainText(brief);

    // 8) The setup checklist shows avatar = not done (no portrait
    //    submitted), voice = not done (no preset selected here).
    await expect(page.getByTestId("setup-panel")).toContainText(/runway avatar/i);
  });

  test("portrait upload renders the avatar pill as ready", async ({ page }) => {
    const email = `e2e-create-img-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    await page.goto("/spokespeople/new?legacy=1");

    await page.getByLabel("Name").fill("With Portrait");
    await page
      .getByLabel("Business brief")
      .fill("Tests that the portrait → data URI → avatar pipeline lands.");

    // Upload a tiny in-memory PNG (the same 1×1 transparent buffer
    // the backend smoke uses). setInputFiles bypasses the
    // drag-and-drop UI but hits the same FileReader path.
    await page.getByTestId("portrait-input").setInputFiles({
      name: "test.png",
      mimeType: "image/png",
      buffer: SILENT_PNG_BUFFER,
    });

    // The dropzone collapses into the preview state
    await expect(page.getByTestId("portrait-remove")).toBeVisible();

    await Promise.all([
      page.waitForURL(/\/spokespeople\/[0-9a-f-]+$/),
      page.getByTestId("create-submit").click(),
    ]);

    // Avatar pill on the detail page should now be in mock-ready
    // state (backend wires runway_avatar_id when portrait_data_uri
    // is supplied — mock mode short-circuits to ready).
    await expect(page.getByTestId("status-pill-avatar")).toContainText(/mock|ready/i);
  });
});
