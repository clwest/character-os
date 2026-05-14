import { test, expect } from "@playwright/test";

// SESSION 138 — K5 spokesperson Knowledge panel.
//
// Exercises the filtered view + attach/detach roundtrip:
//
//   1. Fresh signup → wizard creates a spokesperson
//   2. Ingest a workspace-wide doc via /workspace/knowledge
//   3. Visit /spokespeople/<id> → KnowledgePanel shows the doc
//      with "Workspace-wide" visibility
//   4. Click "Make {name}-only" → row flips to "Restricted"
//      with a Detach button
//   5. Click Detach → row flips back to "Workspace-wide"
//
// Requires the same backend setup as K4 e2e:
//   - Django + Celery running with EMBEDDING_FORCE_MOCK=1
//   - Media-engine + RUNWAY_FORCE_MOCK=1 (for the wizard step)
//   - Postgres + Redis up

const PASSWORD = "playwright-test-pw-x4q9z!";

async function signUp(page: import("@playwright/test").Page): Promise<string> {
  const email = `e2e-k5-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: /create account/i }).click(),
  ]);
  return email;
}

async function createSpokesperson(
  page: import("@playwright/test").Page,
  name: string,
  brief: string,
): Promise<string> {
  // Use the legacy single-form path (?legacy=1) rather than the
  // 4-step wizard. The wizard requires portrait + voice input
  // which is orthogonal to the K5 panel behavior under test
  // here; the legacy form just needs name + brief.
  await page.goto("/spokespeople/new?legacy=1");
  await page.getByLabel("Name").fill(name);
  await page.getByLabel(/business brief/i).fill(brief);

  await Promise.all([
    page.waitForURL(/\/spokespeople\/[0-9a-f-]+$/),
    page.getByTestId("create-submit").click(),
  ]);

  const url = page.url();
  const match = url.match(/\/spokespeople\/([0-9a-f-]+)$/);
  expect(match).toBeTruthy();
  return match![1];
}

test.describe("spokesperson knowledge panel (K5)", () => {
  test("workspace doc shows up; attach narrows visibility; detach restores", async ({
    page,
  }) => {
    await signUp(page);
    const spokespersonId = await createSpokesperson(
      page,
      "K5 Spokesperson",
      "A k5 spokesperson for the panel test fixture content.",
    );

    // Ingest a workspace doc via the K4 paste flow
    await page.goto("/workspace/knowledge");
    await page.getByTestId("paste-title").fill("Shared product brief");
    await page
      .getByTestId("paste-content")
      .fill("Workspace-wide content every spokesperson should see.");
    await page.getByTestId("paste-submit").click();

    // Wait for processed
    await expect(
      page.locator('[data-testid="knowledge-status"]'),
    ).toHaveAttribute("data-status", "processed", { timeout: 30_000 });

    // Visit the spokesperson detail page
    await page.goto(`/spokespeople/${spokespersonId}`);
    await expect(
      page.getByTestId("spokesperson-knowledge-panel"),
    ).toBeVisible();

    // The doc should appear with workspace-wide visibility
    const row = page.locator('[data-testid^="spokesperson-knowledge-row-"]').first();
    await expect(row).toBeVisible({ timeout: 15_000 });
    await expect(row).toHaveAttribute("data-visibility", "workspace-wide");

    // The attach button should read "Make {name}-only"
    const rowTestId = await row.getAttribute("data-testid");
    const docId = rowTestId!.replace("spokesperson-knowledge-row-", "");
    const attachBtn = page.getByTestId(`attach-button-${docId}`);
    await expect(attachBtn).toBeVisible();
    await expect(attachBtn).toContainText(/make.*only/i);

    // Click attach → visibility flips to restricted
    await attachBtn.click();
    await expect(row).toHaveAttribute("data-visibility", "restricted-includes-me", {
      timeout: 10_000,
    });

    // Detach button now visible
    const detachBtn = page.getByTestId(`detach-button-${docId}`);
    await expect(detachBtn).toBeVisible();
    await detachBtn.click();

    // Visibility returns to workspace-wide
    await expect(row).toHaveAttribute("data-visibility", "workspace-wide", {
      timeout: 10_000,
    });
  });

  test("empty state shows when no knowledge is visible", async ({ page }) => {
    await signUp(page);
    const spokespersonId = await createSpokesperson(
      page,
      "Empty Knowledge",
      "A spokesperson with no knowledge attached for the empty-state test.",
    );

    await page.goto(`/spokespeople/${spokespersonId}`);
    await expect(
      page.getByTestId("spokesperson-knowledge-empty"),
    ).toBeVisible();
    // Empty-state offers a link to the workspace knowledge route
    await expect(page.getByTestId("empty-add-knowledge")).toHaveAttribute(
      "href",
      "/workspace/knowledge",
    );
  });
});
