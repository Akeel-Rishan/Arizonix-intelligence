import { defineConfig, devices } from "@playwright/test";

const invalidConfigurationCheck = process.env.EXPECT_INVALID_PUBLIC_CONFIG === "1";
const testPublicApiBaseUrl = invalidConfigurationCheck
  ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1")
  : "http://127.0.0.1:8000";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3100",
    env: {
      ...process.env,
      NEXT_PUBLIC_API_BASE_URL: testPublicApiBaseUrl,
    },
    gracefulShutdown: { signal: "SIGINT", timeout: 1_000 },
    url: "http://127.0.0.1:3100",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
