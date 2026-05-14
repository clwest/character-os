import { test, expect } from "@playwright/test";

// SESSION 138 — K4 workspace knowledge route.
//
// Exercises the end-to-end paste path: fresh signup → navigate
// to /workspace/knowledge → paste content → submit → see the
// row appear with status=processed → delete → row disappears.
//
// Requires `EMBEDDING_FORCE_MOCK=1` on the Django backend (set
// in shell envs OR via Django settings) so the embedding step
// completes synchronously with deterministic vectors instead of
// hitting OpenAI. The smoke + start-here doc both reference
// the same pattern.
//
// Backend Celery: the create endpoint calls
// ``embed_document.delay(...)``. If Celery is running with the
// solo pool (as the local stack defaults to), the task fires
// within a second or two. Polling on the status pill at 3s
// intervals reliably catches the transition.

const PASSWORD = "playwright-test-pw-x4q9z!";

async function signUp(page: import("@playwright/test").Page) {
  const email = `e2e-k4-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: /create account/i }).click(),
  ]);
}

test.describe("workspace knowledge (K4)", () => {
  test("paste → ingest → status flips to processed → delete", async ({
    page,
  }) => {
    await signUp(page);
    await page.goto("/workspace/knowledge");

    await expect(page.getByTestId("knowledge-title")).toBeVisible();
    await expect(page.getByTestId("knowledge-upload")).toBeVisible();

    // Empty state initially — no knowledge-list table.
    await expect(page.getByTestId("knowledge-list")).toBeHidden();

    // The Paste tab is the default.
    await expect(page.getByTestId("tab-paste")).toHaveAttribute(
      "data-state",
      "active",
    );

    await page.getByTestId("paste-title").fill("My first knowledge doc");
    await page
      .getByTestId("paste-content")
      .fill(
        "First paragraph of content for the spokesperson to know about.\n\n" +
          "Second paragraph keeps going with more detail.",
      );

    await page.getByTestId("paste-submit").click();

    // List appears once create resolves.
    await expect(page.getByTestId("knowledge-list")).toBeVisible({
      timeout: 10_000,
    });

    // Status flips to processed within polling window. In eager-
    // celery dev configs this is immediate; in real-celery it
    // takes 1-3 polling cycles.
    const status = page.getByTestId("knowledge-status");
    await expect(status).toHaveAttribute("data-status", "processed", {
      timeout: 30_000,
    });

    // Row title matches what we typed.
    await expect(
      page.getByText("My first knowledge doc"),
    ).toBeVisible();

    // Delete clears the row. (Use a dialog accept handler since
    // the delete button confirms via window.confirm.)
    page.once("dialog", (d) => d.accept());

    // Grab the row id from the list to target the delete button.
    const rowLocator = page.locator('[data-testid^="knowledge-row-"]').first();
    const rowTestId = await rowLocator.getAttribute("data-testid");
    expect(rowTestId).toBeTruthy();
    const docId = rowTestId!.replace("knowledge-row-", "");

    await page.getByTestId(`knowledge-delete-${docId}`).click();

    // Row vanishes (soft delete + list invalidation).
    await expect(page.getByText("My first knowledge doc")).toBeHidden({
      timeout: 10_000,
    });
  });

  test("paste form blocks submit when title or content is blank", async ({
    page,
  }) => {
    await signUp(page);
    await page.goto("/workspace/knowledge");

    const submit = page.getByTestId("paste-submit");
    await expect(submit).toBeDisabled();

    await page.getByTestId("paste-title").fill("Title only");
    await expect(submit).toBeDisabled();

    await page.getByTestId("paste-content").fill("now some content");
    await expect(submit).toBeEnabled();

    // Clear title — disabled again.
    await page.getByTestId("paste-title").fill("");
    await expect(submit).toBeDisabled();
  });

  test("upload tab is reachable + form blocks without a file", async ({
    page,
  }) => {
    await signUp(page);
    await page.goto("/workspace/knowledge");

    await page.getByTestId("tab-upload").click();
    await expect(page.getByTestId("upload-title")).toBeVisible();
    await expect(page.getByTestId("upload-file")).toBeVisible();

    const submit = page.getByTestId("upload-submit");
    await expect(submit).toBeDisabled();

    await page.getByTestId("upload-title").fill("title only");
    // Still no file picked → still disabled.
    await expect(submit).toBeDisabled();
  });
});
