import { test, expect } from "@playwright/test";

// SESSION 129 — Wizard Step 1 (Identity) body (wizard slice 6).
//
// Exercises the Identity step's real form (name + brief + tone
// archetype) + the inline tone suggestion powered by
// GET /api/prompts/suggest-tone/.
//
// Coverage:
//
//   - Brief shorter than 30 chars: no suggestion fires.
//   - Brief that triggers a tutor suggestion ("high school history
//     teacher building lessons for ninth graders"): suggestion
//     renders, click → tone select flips to `tutor`.
//   - Once accepted, the suggestion banner disappears (tone now
//     matches the suggestion).
//   - Manually changing the tone via the select works regardless.
//
// Gate behaviour is covered by wizard-shell.spec.ts. This spec
// focuses on Step 1's specific affordances.

const PASSWORD = "playwright-test-pw-x4q9z!";

async function signUp(page: import("@playwright/test").Page) {
  const email = `e2e-w6-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: /create account/i }).click(),
  ]);
}

test.describe("wizard step 1 — Identity body (slice 6)", () => {
  test("brief triggers a tone suggestion → click → select flips", async ({
    page,
  }) => {
    await signUp(page);
    await page.goto("/spokespeople/new?wizard=1");
    await expect(page.getByTestId("wizard")).toBeVisible();

    const nameInput = page.getByTestId("wizard-name-input");
    const briefInput = page.getByTestId("wizard-brief-input");
    const toneSelect = page.getByTestId("wizard-tone-select");

    // Initial state: tone defaults to `expert`. No suggestion yet
    // (brief is empty).
    await expect(toneSelect).toHaveValue("expert");
    await expect(page.getByTestId("wizard-tone-suggestion")).toBeHidden();

    await nameInput.fill("Mr. Bell, High School History Teacher");
    // Short brief — no suggestion (under the 30-char minimum the
    // useSuggestTone hook enforces client-side).
    await briefInput.fill("Short.");
    await expect(page.getByTestId("wizard-tone-suggestion")).toBeHidden();

    // Long-enough tutor-shaped brief → server returns `tutor` →
    // suggestion banner renders.
    await briefInput.fill(
      "High school history teacher building lesson plans " +
        "for ninth-grade students learning about ancient Rome.",
    );
    const suggestion = page.getByTestId("wizard-tone-suggestion");
    await expect(suggestion).toBeVisible({ timeout: 5_000 });
    await expect(suggestion).toContainText(/tutor/i);

    // Click "Pick tutor →" → select flips → suggestion disappears
    // (the select now matches the suggested value, so showing it
    // would be redundant).
    await page.getByTestId("wizard-tone-suggestion-accept").click();
    await expect(toneSelect).toHaveValue("tutor");
    await expect(suggestion).toBeHidden();

    // Manually flipping the tone via the select still works.
    await toneSelect.selectOption("performer");
    await expect(toneSelect).toHaveValue("performer");
  });

  test("brief too short surfaces an inline validation error", async ({
    page,
  }) => {
    await signUp(page);
    await page.goto("/spokespeople/new?wizard=1");

    const briefInput = page.getByTestId("wizard-brief-input");
    await briefInput.fill("Hi");
    await expect(page.getByTestId("wizard-brief-error")).toBeVisible();
    await expect(page.getByTestId("wizard-brief-error")).toContainText(
      /at least/i,
    );

    // Filling past the floor clears the error.
    await briefInput.fill("Long enough now to clear the validation error.");
    await expect(page.getByTestId("wizard-brief-error")).toBeHidden();
  });
});
