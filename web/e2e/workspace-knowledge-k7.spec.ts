import { test, expect } from "@playwright/test";

// SESSION 140 — K7 workspace knowledge: URL + Search tabs.
//
// Backend must run with EMBEDDING_FORCE_MOCK=1 + SERPER_FORCE_MOCK=1
// so the test stays hermetic (no real network calls). The Django
// stack started in earlier sessions already had EMBEDDING_FORCE_MOCK=1;
// the additional SERPER_FORCE_MOCK=1 is set on restart per
// 00-START-NEXT-SESSION.md.
//
// The URL ingest path itself patches url_fetch on the backend side
// from unit tests; here we exercise the SPA-side wiring without
// triggering a real fetch (operators can paste any URL — the e2e
// just verifies the tab renders + submit blocks correctly without
// actually completing an ingest).

const PASSWORD = "playwright-test-pw-x4q9z!";

async function signUp(page: import("@playwright/test").Page) {
  const email = `e2e-k7-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await Promise.all([
    page.waitForURL("**/dashboard"),
    page.getByRole("button", { name: /create account/i }).click(),
  ]);
}

test.describe("workspace knowledge K7 — URL + Search tabs", () => {
  test("Search tab returns mock results + ingest button on each row", async ({
    page,
  }) => {
    await signUp(page);
    await page.goto("/workspace/knowledge");

    await page.getByTestId("tab-search").click();
    await expect(page.getByTestId("search-query")).toBeVisible();

    // Submit disabled until query has text
    await expect(page.getByTestId("search-submit")).toBeDisabled();

    await page.getByTestId("search-query").fill("character os");
    await expect(page.getByTestId("search-submit")).toBeEnabled();
    await page.getByTestId("search-submit").click();

    // Force-mock returns 8 deterministic results by default
    await expect(page.getByTestId("search-results")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("search-result-1")).toBeVisible();
    await expect(page.getByTestId("search-ingest-1")).toBeVisible();
  });

  test("URL tab is reachable + URL field is required", async ({ page }) => {
    await signUp(page);
    await page.goto("/workspace/knowledge");

    await page.getByTestId("tab-url").click();
    await expect(page.getByTestId("url-input")).toBeVisible();
    await expect(page.getByTestId("url-title")).toBeVisible();

    // Submit blocked when URL is empty
    await expect(page.getByTestId("url-submit")).toBeDisabled();

    // Add URL → enabled
    await page.getByTestId("url-input").fill("https://example.com/test");
    await expect(page.getByTestId("url-submit")).toBeEnabled();
  });

  test("All four tabs render and are switchable", async ({ page }) => {
    await signUp(page);
    await page.goto("/workspace/knowledge");

    // Default — paste
    await expect(page.getByTestId("tab-paste")).toHaveAttribute(
      "data-state", "active",
    );

    await page.getByTestId("tab-upload").click();
    await expect(page.getByTestId("tab-upload")).toHaveAttribute(
      "data-state", "active",
    );

    await page.getByTestId("tab-url").click();
    await expect(page.getByTestId("tab-url")).toHaveAttribute(
      "data-state", "active",
    );

    await page.getByTestId("tab-search").click();
    await expect(page.getByTestId("tab-search")).toHaveAttribute(
      "data-state", "active",
    );
  });
});
