import { test, expect } from "@playwright/test";

// SESSION 133 — Wizard Step 1 template tile picker (wizard slice 10).
//
// Tests the 4-tile picker that pre-fills Step 1's fields when an
// operator clicks a named template (Riggs / Sasha / Donny / Maya).
// The content of those templates is operator-collaborative starter
// material defined in
// `shell/character_os/templates/spokesperson_templates.py`.
//
// Coverage:
//   - All 4 tiles render from the GET /api/spokespeople/templates/
//     endpoint.
//   - Clicking Maya (mascot / tutor — James's classroom use case)
//     pre-fills name + brief + tone + visual_subject.
//   - The chosen template's voice_preset pre-fills the voice bag —
//     Step 3 opens with the preset preview, no manual pick needed.
//   - "Start from scratch" clears the identity fields.
//   - Editing fields after picking still works (template stops
//     being "active" but the state survives).

const PASSWORD = "playwright-test-pw-x4q9z!";

async function signUpAndOpenWizard(
  page: import("@playwright/test").Page,
): Promise<void> {
  const email = `e2e-w10-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: /create account/i }).click(),
  ]);
  await page.goto("/spokespeople/new");
  await expect(page.getByTestId("wizard")).toBeVisible();
}

test.describe("wizard template tiles (slice 10)", () => {
  test("all 4 tiles render + Maya pre-fills Step 1 fields", async ({
    page,
  }) => {
    await signUpAndOpenWizard(page);

    // The picker renders 4 tiles. Test the canonical names — the
    // content can be operator-tuned later without changing the
    // structure.
    const picker = page.getByTestId("wizard-template-picker");
    await expect(picker).toBeVisible();
    await expect(page.getByTestId("wizard-template-riggs")).toBeVisible();
    await expect(page.getByTestId("wizard-template-sasha")).toBeVisible();
    await expect(page.getByTestId("wizard-template-donny")).toBeVisible();
    await expect(page.getByTestId("wizard-template-maya")).toBeVisible();

    // Click Maya — pre-fills identity.
    await page.getByTestId("wizard-template-maya").click();

    await expect(page.getByTestId("wizard-name-input")).toHaveValue("Maya");
    await expect(page.getByTestId("wizard-brief-input")).toContainText(
      /educator|tutor|learner/i,
    );
    await expect(page.getByTestId("wizard-tone-select")).toHaveValue("tutor");

    // Tile shows the active state (aria-pressed).
    await expect(page.getByTestId("wizard-template-maya")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(page.getByTestId("wizard-template-riggs")).toHaveAttribute(
      "aria-pressed",
      "false",
    );

    // Advance through Steps 2 + 3 → confirm the template's
    // visual_subject + voice_preset reached the right places.
    await expect(page.getByTestId("wizard-next")).toBeEnabled();
    await page.getByTestId("wizard-next").click();
    await expect(page.getByTestId("wizard-step-2")).toBeVisible();

    // Step 2 — switch to Generate tab; template select should be
    // pre-selected to `mascot` (Maya's visual_template).
    await page.getByTestId("wizard-portrait-tab-generate").click();
    await expect(
      page.getByTestId("wizard-portrait-template-select"),
    ).toHaveValue("mascot");

    // Drop a tiny PNG to satisfy the gate (testing template
    // threading, not the Generate flow itself).
    const tinyPng = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
      "base64",
    );
    await page.getByTestId("wizard-portrait-tab-upload").click();
    await page.getByTestId("portrait-input").setInputFiles({
      name: "tiny.png",
      mimeType: "image/png",
      buffer: tinyPng,
    });
    await page.getByTestId("wizard-next").click();
    await expect(page.getByTestId("wizard-step-3")).toBeVisible();

    // Step 3 — voice was pre-filled by the template. The voice
    // preview is shown (no tabs), holding the template's preset.
    await expect(page.getByTestId("voice-preview")).toBeVisible();
    // Maya's voice_preset is `victoria` per the starter content.
    await expect(page.getByTestId("voice-preview")).toContainText(/victoria/i);

    // Advance to Step 4 — the review row shows the voice.
    await page.getByTestId("wizard-next").click();
    await expect(page.getByTestId("wizard-step-4")).toBeVisible();
    await expect(page.getByTestId("wizard-confirm-voice")).toContainText(
      /runway preset · victoria/i,
    );
  });

  test("Start from scratch clears identity fields", async ({ page }) => {
    await signUpAndOpenWizard(page);

    // Pick a template first, then click "Start from scratch."
    await page.getByTestId("wizard-template-riggs").click();
    await expect(page.getByTestId("wizard-name-input")).toHaveValue("Riggs");

    await page.getByTestId("wizard-template-clear").click();
    await expect(page.getByTestId("wizard-name-input")).toHaveValue("");
    await expect(page.getByTestId("wizard-brief-input")).toHaveValue("");
    await expect(page.getByTestId("wizard-tone-select")).toHaveValue("expert");

    // No tile is active.
    await expect(page.getByTestId("wizard-template-riggs")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  test("editing after a template pick keeps the typed value", async ({
    page,
  }) => {
    await signUpAndOpenWizard(page);

    await page.getByTestId("wizard-template-sasha").click();
    await expect(page.getByTestId("wizard-name-input")).toHaveValue("Sasha");

    // Edit the name. Tile should drop to inactive (since name no
    // longer matches), but the typed value survives.
    await page.getByTestId("wizard-name-input").fill("Sasha Custom");
    await expect(page.getByTestId("wizard-name-input")).toHaveValue(
      "Sasha Custom",
    );
    await expect(page.getByTestId("wizard-template-sasha")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });
});
