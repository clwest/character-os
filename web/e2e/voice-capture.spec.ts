import { test, expect } from "@playwright/test";

// SESSION 126 — Voice tabs scaffold (wizard slice 3).
//
// Drives the <VoiceCapture> component from the spokesperson detail
// page's setup checklist. Two paths covered end-to-end:
//
//   1. Preset path — pick "vincent" → submit → voice_id persists.
//   2. Upload path — setInputFiles with a tiny silent WAV blob →
//      submit → voice_id persists (mock-mode media-engine returns
//      a deterministic mock voice_id).
//
// The Record path is intentionally skipped: MediaRecorder + the
// synthetic audio stream that Chromium's --use-fake-device flag
// emits is not a reliable combo in CI. Manually verifiable; the
// shape of the recorder code mirrors <CameraCapture> which IS
// covered by portrait-camera.spec.ts.

const PASSWORD = "playwright-test-pw-x4q9z!";

async function signUpAndSeedSpokesperson(
  page: import("@playwright/test").Page,
): Promise<{ spokespersonId: string }> {
  const email = `e2e-voice-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;

  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: /create account/i }).click(),
  ]);

  const me = await (await page.request.get("/api/me/")).json();
  const workspaceId: string = me.default_workspace.id;
  const csrf = (await page.context().cookies()).find(
    (c) => c.name === "csrftoken",
  )?.value;
  expect(csrf).toBeTruthy();

  const created = await page.request.post("/api/spokespeople/", {
    data: {
      workspace: workspaceId,
      name: "Voice Test",
      business_brief: "Spokesperson seeded for voice-capture e2e coverage.",
    },
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf! },
  });
  expect(created.ok()).toBeTruthy();
  const sp = await created.json();
  return { spokespersonId: sp.id };
}

test.describe("voice capture (wizard slice 3)", () => {
  test("preset path: pick vincent → save → voice_id persists", async ({ page }) => {
    const { spokespersonId } = await signUpAndSeedSpokesperson(page);

    await page.goto(`/spokespeople/${spokespersonId}`);
    await expect(page.getByTestId("spokesperson-name")).toContainText("Voice Test");

    // Voice setup is hidden behind a "Set up voice" affordance.
    const openBtn = page.getByTestId("voice-setup-open");
    await expect(openBtn).toBeVisible();
    await openBtn.click();

    // Three tabs visible. Preset is the default.
    await expect(page.getByTestId("voice-tabs")).toBeVisible();
    await expect(page.getByTestId("voice-tab-preset")).toBeVisible();
    await expect(page.getByTestId("voice-tab-upload")).toBeVisible();
    await expect(page.getByTestId("voice-tab-record")).toBeVisible();

    // Pick a preset from the select.
    const select = page.getByTestId("voice-preset-select");
    await expect(select).toBeVisible();
    await select.selectOption("vincent");
    await page.getByTestId("voice-preset-use").click();

    // The preview pill renders + Save voice fires the mutation.
    await expect(page.getByTestId("voice-preview")).toBeVisible();
    await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.url().includes(`/api/spokespeople/${spokespersonId}/clone-voice/`) &&
          resp.request().method() === "POST",
      ),
      page.getByTestId("voice-setup-submit").click(),
    ]);

    // After save, the affordance disappears (voice is bound now —
    // the setup item flips to done + the "Set up voice" row drops
    // out of the unfinished list).
    await expect(page.getByTestId("voice-setup-open")).toBeHidden();
    await expect(page.getByTestId("status-pill-voice")).toContainText(/bound/i);

    // And the metadata grid surfaces the new voice_id.
    await expect(page.getByText(/vincent/i).first()).toBeVisible();
  });

  test("upload path: tiny wav → save → voice_id persists", async ({ page }) => {
    const { spokespersonId } = await signUpAndSeedSpokesperson(page);

    await page.goto(`/spokespeople/${spokespersonId}`);
    await page.getByTestId("voice-setup-open").click();

    // Switch to the Upload tab.
    await page.getByTestId("voice-tab-upload").click();
    const input = page.getByTestId("voice-input");
    await expect(input).toBeAttached();

    // Tiny 1-byte WAV-shaped buffer is enough — the backend writes
    // it to the content-addressed cache and (in mock mode) returns
    // a deterministic voice_id without inspecting the audio bytes.
    const silentWav = Buffer.from([
      0x52, 0x49, 0x46, 0x46, 0x24, 0x00, 0x00, 0x00, 0x57, 0x41, 0x56, 0x45,
      0x66, 0x6d, 0x74, 0x20, 0x10, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
      0x44, 0xac, 0x00, 0x00, 0x88, 0x58, 0x01, 0x00, 0x02, 0x00, 0x10, 0x00,
      0x64, 0x61, 0x74, 0x61, 0x00, 0x00, 0x00, 0x00,
    ]);
    await input.setInputFiles({
      name: "silence.wav",
      mimeType: "audio/wav",
      buffer: silentWav,
    });

    await expect(page.getByTestId("voice-preview")).toBeVisible();
    await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.url().includes(`/api/spokespeople/${spokespersonId}/clone-voice/`) &&
          resp.request().method() === "POST" &&
          resp.ok(),
      ),
      page.getByTestId("voice-setup-submit").click(),
    ]);

    await expect(page.getByTestId("voice-setup-open")).toBeHidden();
    await expect(page.getByTestId("status-pill-voice")).toContainText(/bound/i);
  });
});
