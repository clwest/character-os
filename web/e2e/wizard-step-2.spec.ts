import { test, expect } from "@playwright/test";
import { createWizardWorld } from "./helpers/wizard";

// SESSION 130 — Wizard Step 2 (Portrait) body (wizard slice 7).
//
// Drives the Step 2 body's three-mode tabbed input:
//
//   - Upload — setInputFiles with an in-memory PNG buffer.
//   - Generate — pick template, type subject, submit, assert
//     preview, click Use, assert canAdvance.
//
// Camera path is covered by portrait-camera.spec.ts (SESSION 124's
// <PortraitUpload> wrapper, which Step 2 reuses); not duplicated
// here.
//
// canAdvance gating: Step 2's Next stays disabled until a portrait
// is chosen via any of the three modes.

const PASSWORD = "playwright-test-pw-x4q9z!";

async function signUpAndOpenWizard(
  page: import("@playwright/test").Page,
): Promise<void> {
  const email = `e2e-w7-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: /create account/i }).click(),
  ]);

  await page.goto("/spokespeople/new");
  await expect(page.getByTestId("wizard")).toBeVisible();

  // Step 1 — fill the gate. Brief is long enough to satisfy >= 8.
  await page.getByTestId("wizard-name-input").fill("Step 2 Test");
  await page
    .getByTestId("wizard-brief-input")
    .fill("Sells artisan bicycle bells to small bike shops.");
  await createWizardWorld(page, "Wizard step 2");
  await page.getByTestId("wizard-next").click();
  await expect(page.getByTestId("wizard-step-2")).toBeVisible();
}

test.describe("wizard step 2 — Portrait body (slice 7)", () => {
  test("upload path: setInputFiles → preview → next enables", async ({ page }) => {
    await signUpAndOpenWizard(page);

    // All three tabs render. Upload is default.
    await expect(page.getByTestId("wizard-portrait-tabs")).toBeVisible();
    await expect(page.getByTestId("wizard-portrait-tab-upload")).toBeVisible();
    await expect(page.getByTestId("wizard-portrait-tab-camera")).toBeVisible();
    await expect(page.getByTestId("wizard-portrait-tab-generate")).toBeVisible();

    // Next is gated until a portrait is chosen.
    const next = page.getByTestId("wizard-next");
    await expect(next).toBeDisabled();

    // Upload tab — drop a tiny PNG into the hidden file input. The
    // testid is owned by the shared `<UploadDropzone>` component
    // (exported from portrait-upload.tsx).
    const tinyPng = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
      "base64",
    );
    await page.getByTestId("portrait-input").setInputFiles({
      name: "tiny.png",
      mimeType: "image/png",
      buffer: tinyPng,
    });

    // Preview renders + Change button appears + Next enables.
    await expect(page.getByTestId("wizard-portrait-preview")).toBeVisible();
    await expect(page.getByTestId("wizard-portrait-change")).toBeVisible();
    await expect(next).toBeEnabled();

    // Click Change → preview goes away → Next disables again. The
    // tab strip should come back too.
    await page.getByTestId("wizard-portrait-change").click();
    await expect(page.getByTestId("wizard-portrait-preview")).toBeHidden();
    await expect(page.getByTestId("wizard-portrait-tabs")).toBeVisible();
    await expect(next).toBeDisabled();
  });

  test("generate path: pick template + subject → preview → use", async ({
    page,
  }) => {
    await signUpAndOpenWizard(page);

    // Switch to the Generate tab.
    await page.getByTestId("wizard-portrait-tab-generate").click();
    await expect(page.getByTestId("wizard-portrait-generate")).toBeVisible();

    // Pick the mascot template + type James's battle unicorn subject.
    await page
      .getByTestId("wizard-portrait-template-select")
      .selectOption("mascot");
    await page
      .getByTestId("wizard-portrait-subject-input")
      .fill("armored battle unicorn warrior");

    // Submit → POST /api/spokespeople/generate-portrait/ → preview
    // renders (mock-mode returns a deterministic placeholder PNG).
    await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.url().endsWith("/api/spokespeople/generate-portrait/") &&
          resp.request().method() === "POST" &&
          resp.ok(),
      ),
      page.getByTestId("wizard-portrait-generate-submit").click(),
    ]);

    const preview = page.getByTestId("wizard-portrait-generate-preview");
    await expect(preview).toBeVisible({ timeout: 10_000 });
    await expect(preview).toContainText(/mock-mode/i);

    // Click "Use this portrait" → committed-preview replaces the
    // generate panel + Next enables.
    await page.getByTestId("wizard-portrait-use").click();
    await expect(page.getByTestId("wizard-portrait-preview")).toBeVisible();
    await expect(page.getByTestId("wizard-next")).toBeEnabled();

    // Advance to Step 3 → confirms state threading worked end-to-end.
    await page.getByTestId("wizard-next").click();
    await expect(page.getByTestId("wizard-step-3")).toBeVisible();
  });
});
