import { test, expect } from "@playwright/test";

// SESSION 134 — Hide-on-completion (wizard slice 11).
//
// The detail page's setup checklist used to render in two modes:
// a "Ready to render" message inside the panel when fully
// configured, or the full checklist (with done items struck through)
// when partial.
//
// W11 reshapes this:
//   - Fully configured (avatar bound + voice set + brief filled):
//     no setup panel at all + a "Ready to render" badge in the
//     masthead. The videos panel takes full width.
//   - Partial: setup panel renders only the *unfinished* items.
//
// This spec covers both states using two seed paths:
//   1. Full wizard run → fully-configured row → assert no panel +
//      ready badge visible.
//   2. API-seeded brief-only row → partial → assert panel renders
//      with the avatar + voice rows, no brief row (it's done).

const PASSWORD = "playwright-test-pw-x4q9z!";

test.describe("detail page hide-on-completion (slice 11)", () => {
  test("fully-configured row: no checklist + ready badge", async ({
    page,
  }) => {
    const email = `e2e-w11-full-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const name = "Fully Configured Test";
    const brief =
      "Sells artisan bicycle bells to small bike shops. Warm, opinionated, just-the-facts.";

    // 1) Sign up + run the wizard end-to-end (drops a portrait +
    //    picks the vincent preset → fully configured).
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(PASSWORD);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);
    await page.goto("/spokespeople/new");
    await page.getByTestId("wizard-name-input").fill(name);
    await page.getByTestId("wizard-brief-input").fill(brief);
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
    await page.getByTestId("voice-preset-select").selectOption("vincent");
    await page.getByTestId("voice-preset-use").click();
    await page.getByTestId("wizard-next").click();
    await Promise.all([
      page.waitForURL(/\/spokespeople\/[0-9a-f-]+$/),
      page.getByTestId("wizard-next").click(),
    ]);

    // 2) Detail page assertions: ready badge visible, no setup panel.
    await expect(page.getByTestId("spokesperson-detail")).toHaveAttribute(
      "data-configured",
      "full",
    );
    await expect(page.getByTestId("ready-badge")).toBeVisible();
    await expect(page.getByTestId("ready-state")).toBeVisible();
    await expect(page.getByTestId("setup-panel")).toBeHidden();
  });

  test("partial row: setup panel shows only unfinished items", async ({
    page,
  }) => {
    const email = `e2e-w11-part-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(PASSWORD);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    // Seed a partial row directly via the API: brief filled, no
    // portrait → avatar not bound + voice not set.
    const me = await (await page.request.get("/api/me/")).json();
    const csrf = (await page.context().cookies()).find(
      (c) => c.name === "csrftoken",
    )?.value;
    const created = await page.request.post("/api/spokespeople/", {
      data: {
        workspace: me.default_workspace.id,
        name: "Partial Row Test",
        business_brief: "Test row — partial configuration coverage.",
      },
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf! },
    });
    expect(created.ok()).toBeTruthy();
    const sp = await created.json();

    await page.goto(`/spokespeople/${sp.id}`);

    // Detail page reports partial state, no ready badge.
    await expect(page.getByTestId("spokesperson-detail")).toHaveAttribute(
      "data-configured",
      "partial",
    );
    await expect(page.getByTestId("ready-badge")).toBeHidden();

    // Setup panel renders. The brief is done (we filled it on
    // create), so its row is gone. Avatar + voice rows remain.
    await expect(page.getByTestId("setup-panel")).toBeVisible();
    await expect(page.getByTestId("setup-item-brief")).toBeHidden();
    await expect(page.getByTestId("setup-item-avatar")).toBeVisible();
    await expect(page.getByTestId("setup-item-voice")).toBeVisible();
  });
});
