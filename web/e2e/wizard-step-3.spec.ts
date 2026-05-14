import { test, expect } from "@playwright/test";

// SESSION 131 — Wizard Step 3 (Voice) body (wizard slice 8).
//
// Drives the Step 3 body's three-mode voice input (the SESSION 126
// <VoiceCapture> component re-used inside the wizard reducer) plus
// the new Skip affordance.
//
// Coverage:
//
//   - All 3 tabs render (Preset / Upload / Record).
//   - Preset path: pick a voice → committed-preview → advance to Step 4.
//   - Upload path: drop a tiny WAV → committed-preview → advance.
//   - Skip path: click Skip → land on Step 4 (no value chosen via the
//     UI). State should hold the default Runway preset.
//
// The Record path is intentionally skipped — synthetic audio +
// MediaRecorder in CI is flaky (same deferral as SESSION 126's
// voice-capture.spec.ts on the detail page).
//
// Step 3 is OPTIONAL by design (the voice has a sane default), so
// canAdvance(step=3) doesn't gate. The "all 3 paths" coverage proves
// state threading works regardless of which path the operator picks.

const PASSWORD = "playwright-test-pw-x4q9z!";

async function signUpAndReachStep3(
  page: import("@playwright/test").Page,
): Promise<void> {
  const email = `e2e-w8-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: /create account/i }).click(),
  ]);

  await page.goto("/spokespeople/new?wizard=1");
  await expect(page.getByTestId("wizard")).toBeVisible();

  // Step 1 — fill identity.
  await page.getByTestId("wizard-name-input").fill("Step 3 Test");
  await page
    .getByTestId("wizard-brief-input")
    .fill("Sells artisan bicycle bells to small bike shops.");
  await page.getByTestId("wizard-next").click();
  await expect(page.getByTestId("wizard-step-2")).toBeVisible();

  // Step 2 — drop a portrait via Upload.
  const tinyPng = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
    "base64",
  );
  await page.getByTestId("portrait-input").setInputFiles({
    name: "tiny.png",
    mimeType: "image/png",
    buffer: tinyPng,
  });
  await page.getByTestId("wizard-next").click();
  await expect(page.getByTestId("wizard-step-3")).toBeVisible();
}

test.describe("wizard step 3 — Voice body (slice 8)", () => {
  test("preset path: pick a voice → preview → advance", async ({ page }) => {
    await signUpAndReachStep3(page);

    // All 3 tabs render (the existing <VoiceCapture> contract).
    await expect(page.getByTestId("voice-tabs")).toBeVisible();
    await expect(page.getByTestId("voice-tab-preset")).toBeVisible();
    await expect(page.getByTestId("voice-tab-upload")).toBeVisible();
    await expect(page.getByTestId("voice-tab-record")).toBeVisible();

    // Pick vincent from the preset select.
    const select = page.getByTestId("voice-preset-select");
    await expect(select).toBeVisible();
    await select.selectOption("vincent");
    await page.getByTestId("voice-preset-use").click();

    // Preview replaces the tabs.
    await expect(page.getByTestId("voice-preview")).toBeVisible();
    await expect(page.getByTestId("voice-preview")).toContainText(/vincent/i);

    // Advance to Step 4.
    await page.getByTestId("wizard-next").click();
    await expect(page.getByTestId("wizard-step-4")).toBeVisible();

    // The assembled payload (rendered via Step 4's DebugState) shows
    // the preset committed.
    const debug = page.getByTestId("wizard-debug-state");
    await expect(debug).toContainText(/vincent/);
    await expect(debug).toContainText(/preset/);
  });

  test("upload path: drop wav → preview → advance", async ({ page }) => {
    await signUpAndReachStep3(page);

    await page.getByTestId("voice-tab-upload").click();
    // Tiny WAV header (44 bytes, zero data). Mock-mode backend
    // doesn't inspect bytes; we just need a wav-shaped file under
    // the 15 MB cap.
    const silentWav = Buffer.from([
      0x52, 0x49, 0x46, 0x46, 0x24, 0x00, 0x00, 0x00, 0x57, 0x41, 0x56, 0x45,
      0x66, 0x6d, 0x74, 0x20, 0x10, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
      0x44, 0xac, 0x00, 0x00, 0x88, 0x58, 0x01, 0x00, 0x02, 0x00, 0x10, 0x00,
      0x64, 0x61, 0x74, 0x61, 0x00, 0x00, 0x00, 0x00,
    ]);
    await page.getByTestId("voice-input").setInputFiles({
      name: "silence.wav",
      mimeType: "audio/wav",
      buffer: silentWav,
    });

    await expect(page.getByTestId("voice-preview")).toBeVisible();
    await expect(page.getByTestId("voice-preview")).toContainText(
      /silence\.wav/,
    );

    await page.getByTestId("wizard-next").click();
    await expect(page.getByTestId("wizard-step-4")).toBeVisible();

    // The payload debug shows the upload data URI was supplied.
    const debug = page.getByTestId("wizard-debug-state");
    await expect(debug).toContainText(/upload/);
    await expect(debug).toContainText(/supplied/);
  });

  test("skip path: click Skip → land on Step 4 with default preset", async ({
    page,
  }) => {
    await signUpAndReachStep3(page);

    // No voice picked. Click Skip — wizard pre-fills `vincent` +
    // advances.
    await page.getByTestId("wizard-voice-skip").click();
    await expect(page.getByTestId("wizard-step-4")).toBeVisible();

    const debug = page.getByTestId("wizard-debug-state");
    await expect(debug).toContainText(/vincent/);
    await expect(debug).toContainText(/preset/);
  });
});
