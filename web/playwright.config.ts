import { defineConfig, devices } from "@playwright/test";

// End-to-end smoke tests. The mirror of `python manage.py smoke_*`
// on the backend. See `docs/design/SPA_ARCHITECTURE.md`
// §"Smoke test pattern" for the contract.
//
// Local dev run:
//   1. Bring up the backend stack (Django :8000 + media-engine + Redis)
//   2. `pnpm e2e:install`  (one-time, downloads browsers)
//   3. `pnpm e2e`
//
// Playwright spawns its own Vite dev server on :5173 via `webServer`;
// the Vite proxy forwards /api + /_allauth to :8000.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5174",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:5174",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
