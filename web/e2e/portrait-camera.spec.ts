import { test, expect } from "@playwright/test";

// SESSION 124 — Camera capture for <PortraitUpload>.
//
// Drives the Camera tab end-to-end: sign up → /spokespeople/new
// → switch to the Camera tab → wait for the synthetic stream to
// go live → click Take picture → preview shows → submit → land on
// the detail page with the avatar bound (mock mode).
//
// Chromium ships with --use-fake-ui-for-media-stream +
// --use-fake-device-for-media-stream flags (configured in
// playwright.config.ts) so getUserMedia auto-grants and returns a
// deterministic synthetic stream. No real camera required.

test.describe("portrait camera capture (wizard slice 1)", () => {
  test("fresh signup → camera tab → capture → submit → detail", async ({ page }) => {
    const email = `e2e-cam-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";
    const name = "Camera Test Spokesperson";
    const brief = "Test spokesperson created via the in-browser camera capture path.";

    // 1) Sign up
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    // 2) Go to the create form
    await page.goto("/spokespeople/new?legacy=1");
    await page.getByLabel("Name").fill(name);
    await page.getByLabel("Business brief").fill(brief);

    // 3) The Portrait section has tabs (Upload | Camera) because
    //    Chromium reports getUserMedia support.
    await expect(page.getByTestId("portrait-tabs")).toBeVisible();
    await expect(page.getByTestId("portrait-tab-upload")).toBeVisible();
    await expect(page.getByTestId("portrait-tab-camera")).toBeVisible();

    // 4) Switch to the Camera tab → CameraCapture mounts →
    //    getUserMedia → stream goes live.
    await page.getByTestId("portrait-tab-camera").click();
    const panel = page.getByTestId("camera-panel");
    await expect(panel).toBeVisible();
    const preview = page.getByTestId("camera-preview");
    await expect(preview).toBeVisible();

    // 5) Wait for the synthetic stream to actually attach. The
    //    Capture button stays disabled until state === "live"
    //    (the useEffect resolves getUserMedia and the videoRef is
    //    populated). Playwright's auto-waiting handles the rest.
    const capture = page.getByTestId("camera-capture");
    await expect(capture).toBeEnabled({ timeout: 10_000 });

    // 6) Click Take picture → drawImage → toDataURL → onChange
    //    fires → preview branch renders.
    await capture.click();

    // 7) The preview-with-Remove pattern (shared with Upload mode).
    //    Filename is auto-derived ("camera-{timestamp}.png").
    const remove = page.getByTestId("portrait-remove");
    await expect(remove).toBeVisible({ timeout: 5_000 });
    // sanity-check the filename starts with our camera- prefix
    await expect(page.getByText(/camera-\d+\.png/)).toBeVisible();

    // 8) Submit the create form → land on detail page
    await Promise.all([
      page.waitForURL(/\/spokespeople\/[0-9a-f-]+$/),
      page.getByTestId("create-submit").click(),
    ]);

    // 9) Detail page renders + avatar pill flips to mock-ready
    //    (the backend's SESSION 116 perform_create fires the
    //    media-engine avatar create when portrait_data_uri is
    //    supplied, regardless of source).
    await expect(page.getByTestId("spokesperson-name")).toContainText(name);
    await expect(page.getByTestId("status-pill-avatar")).toContainText(/mock|ready/i);
  });

  test("upload tab still works when present alongside camera", async ({ page }) => {
    // Belt-and-braces: tabbed refactor shouldn't break the existing
    // file-upload path. Spec is shorter — full lifecycle is covered
    // by create-spokesperson.spec.ts and make-video.spec.ts.
    const email = `e2e-cam-up-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";
    const png = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
      "base64",
    );

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    await page.goto("/spokespeople/new?legacy=1");
    await page.getByLabel("Name").fill("Upload Tab Smoke");
    await page.getByLabel("Business brief").fill("Confirms upload tab is intact post-refactor.");

    // Upload tab is default; the dropzone + hidden input should be
    // visible without explicitly clicking the tab.
    await expect(page.getByTestId("portrait-dropzone")).toBeVisible();
    await page.getByTestId("portrait-input").setInputFiles({
      name: "tiny.png",
      mimeType: "image/png",
      buffer: png,
    });
    await expect(page.getByTestId("portrait-remove")).toBeVisible();
  });
});
