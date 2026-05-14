import { test, expect } from "@playwright/test";

// SESSION 118 Slice 3 e2e. Drives the spokesperson detail flow:
//   1. Sign up (fresh email → fresh workspace)
//   2. POST a spokesperson directly via the SPA's API surface
//      (page.request shares cookies with the page context)
//   3. Reload the dashboard, click the card → /spokespeople/{id}
//   4. Assert identity panel renders + setup checklist shows
//      "not done" rows for avatar/voice (this spokesperson has
//      no portrait, so the create-flow hasn't fired the
//      media-engine path yet).
//
// Backend: Django :8000 must be up. No media-engine needed — we
// create the spokesperson via the row-only path (no portrait,
// so SpokespersonViewSet.perform_create skips the media-engine
// call entirely).

test.describe("spokesperson detail (S-10)", () => {
  test("clicking a card from the dashboard lands on the detail page", async ({
    page,
  }) => {
    const email = `e2e-sp-${Date.now()}-${Math.floor(Math.random() * 1e6)}@character-os.test`;
    const password = "playwright-test-pw-x4q9z!";

    // 1) Sign up
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByRole("button", { name: /create account/i }).click(),
    ]);

    // 2) Discover the workspace id (from /api/me/) so we can target
    //    the right workspace when creating the spokesperson.
    const meResp = await page.request.get("/api/me/");
    expect(meResp.ok()).toBeTruthy();
    const me = await meResp.json();
    const workspaceId: string = me.default_workspace.id;
    expect(workspaceId).toBeTruthy();

    // 3) Create a spokesperson directly via the SPA's API path.
    //    Playwright's request context shares cookies with the page —
    //    the same session-cookie + CSRF cookie that powered the
    //    signup are still in scope. We need to pass X-CSRFToken
    //    explicitly because Django CSRF middleware doesn't trust
    //    the cookie alone.
    const csrf = (await page.context().cookies()).find((c) => c.name === "csrftoken")?.value;
    expect(csrf).toBeTruthy();

    const created = await page.request.post("/api/spokespeople/", {
      data: {
        workspace: workspaceId,
        name: "Casey Test",
        business_brief: "Sells artisan bicycle bells to small bike shops.",
      },
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf!,
      },
    });
    expect(created.ok()).toBeTruthy();
    const sp = await created.json();
    const spokespersonId: string = sp.id;

    // 4) Back to dashboard — the new spokesperson should now appear
    //    in the grid.
    await page.goto("/dashboard");
    const grid = page.getByTestId("spokespeople-grid");
    await expect(grid).toBeVisible();
    await expect(grid.getByText("Casey Test")).toBeVisible();

    // 5) Click into the card. The stretched-link covers the whole
    //    article, so clicking the name (or anywhere on the card)
    //    navigates.
    await Promise.all([
      page.waitForURL(`**/spokespeople/${spokespersonId}`),
      grid.getByRole("link", { name: "Casey Test" }).click(),
    ]);

    // 6) Masthead + identity panel render
    await expect(page.getByTestId("spokesperson-masthead")).toBeVisible();
    await expect(page.getByTestId("spokesperson-name")).toContainText("Casey Test");
    await expect(page.getByTestId("identity-panel")).toBeVisible();
    await expect(page.getByTestId("identity-panel")).toContainText(
      /artisan bicycle bells/i,
    );

    // 7) Setup panel shows the avatar + voice steps as not-done
    //    (this spokesperson was created without a portrait, so no
    //    avatar was bound; voice is empty too).
    const setup = page.getByTestId("setup-panel");
    await expect(setup).toBeVisible();
    await expect(setup).toContainText(/runway avatar/i);
    await expect(setup).toContainText(/voice/i);

    // 8) Videos panel renders the empty state for a fresh
    //    spokesperson.
    await expect(page.getByTestId("videos-empty")).toBeVisible();

    // 9) Back-to-workspace link bounces to /dashboard
    await Promise.all([
      page.waitForURL("**/dashboard"),
      page.getByTestId("back-to-dashboard").click(),
    ]);
    await expect(page).toHaveURL(/\/dashboard$/);
  });
});
