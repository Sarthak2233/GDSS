import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright e2e config - intentionally scoped to web/e2e so vitest
 * component tests under web/tests are never collected.
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  use: {
    ...devices["Desktop Chrome"],
    trace: "on-first-retry",
  },
});
