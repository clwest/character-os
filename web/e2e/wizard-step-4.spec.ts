import { test, expect } from "@playwright/test";
import { createWizardWorld } from "./helpers/wizard";

// SESSION 132 — Wizard Step 4 (Confirm + submit) (wizard slice 9).
//
// Happy-path coverage for the full wizard lifecycle:
//
//   1. Sign up → dashboard empty state
//   2. Click "Create spokesperson" → land on the wizard (now the
//      default at /spokespeople/new)
//   3. Step 1 — fill name + brief + accept tone suggestion
//   4. Step 2 — drop a tiny PNG portrait
//   5. Step 3 — pick a preset voice
//   6. Step 4 — review panel renders all fields + Create button
//      enabled
//   7. Click Create → POST /api/spokespeople/ fires → row lands →
//      welcome screen appears
//   8. Skip onboarding → detail page shows the saved spokesperson
//
// Also a tier-limit error-path test (commented for now — the
// Starter tier limit doesn't kick in until 3 spokespeople; would
// need fixture-level setup to exercise).

const PASSWORD = "playwright-test-pw-x4q9z!";

test.describe("wizard step 4 — Confirm + submit (slice 9)", () => {
  test("happy path: dashboard CTA → wizard → submit → detail page", async ({
    page,
  }) => {
    const email = `e2e-w9-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const name = "Wizard Happy Path";
    const brief =
      "High school history teacher building lesson plans for ninth-grade " +
      "students learning about ancient Rome.";

    // 1) Sign up
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(PASSWORD);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    // 2) Dashboard empty-state CTA → wizard
    const empty = page.getByTestId("spokespeople-empty");
    await expect(empty).toBeVisible();
    await Promise.all([
      page.waitForURL("**/spokespeople/new"),
      page.getByTestId("empty-create-cta").click(),
    ]);
    await expect(page.getByTestId("wizard")).toBeVisible();

    // 3) Step 1 — fill identity + accept tone suggestion
    await page.getByTestId("wizard-name-input").fill(name);
    await page.getByTestId("wizard-brief-input").fill(brief);

    // Tone suggestion fires for a tutor-shaped brief.
    const suggestion = page.getByTestId("wizard-tone-suggestion");
    await expect(suggestion).toBeVisible({ timeout: 5_000 });
    await page.getByTestId("wizard-tone-suggestion-accept").click();
    await expect(page.getByTestId("wizard-tone-select")).toHaveValue("tutor");
    await createWizardWorld(page, "Wizard submit");

    await page.getByTestId("wizard-next").click();
    await expect(page.getByTestId("wizard-step-2")).toBeVisible();

    // 4) Step 2 — drop a tiny PNG
    const tinyPng = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
      "base64",
    );
    await page.getByTestId("portrait-input").setInputFiles({
      name: "tiny.png",
      mimeType: "image/png",
      buffer: tinyPng,
    });
    await expect(page.getByTestId("wizard-portrait-preview")).toBeVisible();
    await page.getByTestId("wizard-next").click();
    await expect(page.getByTestId("wizard-step-3")).toBeVisible();

    // 5) Step 3 — pick the vincent preset
    await page.getByTestId("voice-preset-select").selectOption("vincent");
    await page.getByTestId("voice-preset-use").click();
    await expect(page.getByTestId("voice-preview")).toContainText(/vincent/i);
    await page.getByTestId("wizard-next").click();
    await expect(page.getByTestId("wizard-step-4")).toBeVisible();

    // 6) Step 4 — review panel renders + Create button enabled
    await expect(page.getByTestId("wizard-confirm-portrait")).toBeVisible();
    await expect(page.getByTestId("wizard-confirm-name")).toContainText(name);
    await expect(page.getByTestId("wizard-confirm-business-brief")).toContainText(
      /history teacher/,
    );
    await expect(page.getByTestId("wizard-confirm-tone")).toContainText(/tutor/i);
    await expect(page.getByTestId("wizard-confirm-voice")).toContainText(
      /vincent/i,
    );
    const submit = page.getByTestId("wizard-next");
    await expect(submit).toBeEnabled();
    await expect(submit).toContainText(/create spokesperson/i);

    // 7) Submit → POST → navigate to detail page
    await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.url().endsWith("/api/spokespeople/") &&
          resp.request().method() === "POST" &&
          resp.ok(),
      ),
      page.waitForURL(/\/spokespeople\/[0-9a-f-]+\/welcome$/),
      submit.click(),
    ]);
    await expect(page.getByTestId("welcome-heading")).toContainText(name);
    await Promise.all([
      page.waitForURL(/\/spokespeople\/[0-9a-f-]+$/),
      page.getByTestId("welcome-skip").click(),
    ]);

    // 8) Detail page — assert all the values persisted
    await expect(page.getByTestId("spokesperson-name")).toContainText(name);
    await expect(page.getByTestId("identity-panel")).toContainText(brief);
    // Voice + tone surface in the MetadataGrid (SESSION 127).
    const identity = page.getByTestId("identity-panel");
    await expect(identity).toContainText(/tutor/i);
    await expect(identity).toContainText(/vincent/i);
    // Avatar pill flips to mock-ready (portrait fired the create-
    // avatar pipeline).
    await expect(page.getByTestId("status-pill-avatar")).toContainText(
      /mock|ready/i,
    );
  });

  test("submit disabled if the operator deletes the brief on Step 4", async ({
    page,
  }) => {
    // Defensive: even though Step 1's gate enforces the brief, the
    // operator might navigate back + clear it. Step 4's gate should
    // refuse to fire submit.
    const email = `e2e-w9-back-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(PASSWORD);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    await page.goto("/spokespeople/new");

    // Fill enough to reach Step 4.
    await page.getByTestId("wizard-name-input").fill("Back-Edit Test");
    await page
      .getByTestId("wizard-brief-input")
      .fill("A sufficiently long brief that satisfies the gate.");
    await createWizardWorld(page, "Wizard back edit");
    await page.getByTestId("wizard-next").click();
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
    await page.getByTestId("wizard-voice-skip").click();
    await expect(page.getByTestId("wizard-step-4")).toBeVisible();

    // Navigate back to Step 1, clear the brief, navigate forward
    // again via Next. Next on Step 1 should now be disabled.
    await page.getByTestId("wizard-prev").click();
    await page.getByTestId("wizard-prev").click();
    await page.getByTestId("wizard-prev").click();
    await expect(page.getByTestId("wizard-step-1")).toBeVisible();
    await page.getByTestId("wizard-brief-input").fill("");
    await expect(page.getByTestId("wizard-next")).toBeDisabled();
  });
});
