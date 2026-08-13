import { test, expect } from "@playwright/test";

// SESSION 128 — Wizard scaffold (wizard slice 5).
//
// Drives the wizard shell behind the ?wizard=1 query gate. The
// scaffold itself doesn't create a spokesperson — slices 6-9 fill
// each step's body in. What this spec verifies:
//
//   - All 4 steps render their kicker/title/body
//   - Step indicator reflects the current step (pill highlight +
//     aria-current)
//   - Next is gated on canAdvance (Step 1 needs a name)
//   - Back navigation works
//   - State is preserved across forward + backward navigation
//   - The placeholder Create button on Step 4 stays disabled (until
//     slice 9 wires the real submit)
//   - The legacy form at /spokespeople/new (no query param) is
//     unchanged
//
// The wizard is behind an opt-in flag (?wizard=1) so the existing
// create-spokesperson specs stay green. When slice 9 ships, the
// default flips + this spec gets a happy-path companion.

const PASSWORD = "playwright-test-pw-x4q9z!";

async function signUp(page: import("@playwright/test").Page) {
  const email = `e2e-wiz-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: /create account/i }).click(),
  ]);
}

test.describe("wizard scaffold (slice 5)", () => {
  test("4-step navigation + state preservation", async ({ page }) => {
    await signUp(page);

    // Land on the wizard route (opt-in via query gate).
    await page.goto("/spokespeople/new");
    await expect(page.getByTestId("wizard")).toBeVisible();

    // Step indicator shows 4 pills; pill 1 is current.
    const indicator = page.getByTestId("wizard-step-indicator");
    await expect(indicator).toBeVisible();
    await expect(page.getByTestId("step-pill-1")).toHaveAttribute(
      "aria-current",
      "step",
    );
    await expect(page.getByTestId("step-pill-2")).not.toHaveAttribute(
      "aria-current",
      "step",
    );

    // Step 1 renders Identity + the placeholder name input.
    await expect(page.getByTestId("wizard-step-1")).toBeVisible();
    await expect(page.getByText(/Step 1 of 4/i)).toBeVisible();

    // Next is gated until name AND a long-enough brief are typed
    // (SESSION 129 — slice 6 tightened the gate beyond just-a-name).
    const next = page.getByTestId("wizard-next");
    await expect(next).toBeDisabled();

    const nameInput = page.getByTestId("wizard-name-input");
    const briefInput = page.getByTestId("wizard-brief-input");
    await nameInput.fill("Wizard Test Spokesperson");
    // Brief alone is too short — Next still disabled.
    // (5 chars; the gate floor is 8.)
    await briefInput.fill("Short");
    await expect(next).toBeDisabled();
    // Push brief past the 8-char floor → Next enables.
    await briefInput.fill(
      "Sells artisan bicycle bells to small bike shops.",
    );
    await expect(next).toBeEnabled();

    // Advance to Step 2.
    await next.click();
    await expect(page.getByTestId("wizard-step-2")).toBeVisible();
    await expect(page.getByText(/Step 2 of 4/i)).toBeVisible();
    await expect(page.getByTestId("step-pill-2")).toHaveAttribute(
      "aria-current",
      "step",
    );

    // Step 2 (SESSION 130 — slice 7) gates Next on a chosen
    // portrait. Drop a tiny PNG via the Upload tab to unblock.
    await expect(next).toBeDisabled();
    const tinyPng = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
      "base64",
    );
    await page.getByTestId("portrait-input").setInputFiles({
      name: "tiny.png",
      mimeType: "image/png",
      buffer: tinyPng,
    });
    await expect(next).toBeEnabled();

    // Advance to Step 3 (scaffold accepts unconditionally).
    await next.click();
    await expect(page.getByTestId("wizard-step-3")).toBeVisible();
    await expect(page.getByText(/Step 3 of 4/i)).toBeVisible();

    // Advance to Step 4 (Confirm).
    await next.click();
    await expect(page.getByTestId("wizard-step-4")).toBeVisible();
    await expect(page.getByText(/Step 4 of 4/i)).toBeVisible();

    // On Step 4 (SESSION 132 — slice 9 wired the submit), the
    // primary button reads "Create spokesperson" and is enabled when
    // all upstream gates pass. We don't click — that's covered by
    // wizard-step-4.spec.ts. Here we just verify the navigation +
    // gating shape.
    await expect(next).toContainText(/create spokesperson/i);
    await expect(next).toBeEnabled();

    // Navigate back all the way to Step 1.
    const prev = page.getByTestId("wizard-prev");
    await prev.click();
    await expect(page.getByTestId("wizard-step-3")).toBeVisible();
    await prev.click();
    await expect(page.getByTestId("wizard-step-2")).toBeVisible();
    await prev.click();
    await expect(page.getByTestId("wizard-step-1")).toBeVisible();

    // State preservation: the name we typed earlier is still there.
    await expect(nameInput).toHaveValue("Wizard Test Spokesperson");

    // Back button on Step 1 is disabled.
    await expect(prev).toBeDisabled();
  });

  test("cancel returns to the dashboard", async ({ page }) => {
    await signUp(page);
    await page.goto("/spokespeople/new");

    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByTestId("wizard-cancel").click(),
    ]);
  });

  test("wizard is the default at /spokespeople/new (no flag)", async ({
    page,
  }) => {
    await signUp(page);
    // SESSION 132 flipped the route: wizard is the default; legacy
    // form lives behind ?legacy=1 as an escape hatch.
    await page.goto("/spokespeople/new");
    await expect(page.getByTestId("wizard")).toBeVisible();
    await expect(page.getByTestId("create-submit")).toBeHidden();
  });

  test("legacy form still serves ?legacy=1 (escape hatch)", async ({
    page,
  }) => {
    await signUp(page);
    await page.goto("/spokespeople/new?legacy=1");
    await expect(page.getByTestId("wizard")).toBeHidden();
    await expect(page.getByTestId("create-submit")).toBeVisible();
  });
});
