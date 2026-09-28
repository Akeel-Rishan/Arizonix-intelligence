import { spawn, type ChildProcess } from "node:child_process";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { signIn } from "./support/auth";

const runLiveIntegration = process.env.RUN_LIVE_INTEGRATION === "1";
const apiPort = 8011;
const apiDirectory = path.resolve(process.cwd(), "../api");
const pythonExecutable = path.join(
  apiDirectory,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);

async function startApi(): Promise<ChildProcess> {
  const child = spawn(
    pythonExecutable,
    ["-m", "uvicorn", "arizonix_api.main:app", "--host", "127.0.0.1", "--port", String(apiPort)],
    {
      cwd: apiDirectory,
      env: {
        ...process.env,
        ARIZONIX_ALLOWED_ORIGINS: "http://127.0.0.1:3100",
        ARIZONIX_APP_ENVIRONMENT: "test",
        ARIZONIX_APP_VERSION: "0.1.0",
        ARIZONIX_LOG_LEVEL: "info",
      },
      stdio: "ignore",
    },
  );

  await expect
    .poll(
      async () => {
        try {
          return (await fetch(`http://127.0.0.1:${apiPort}/api/v1/health`)).ok;
        } catch {
          return false;
        }
      },
      { timeout: 15_000 },
    )
    .toBe(true);
  return child;
}

async function stopApi(child: ChildProcess): Promise<void> {
  if (child.exitCode !== null) return;
  child.kill();
  await new Promise<void>((resolve) => child.once("exit", () => resolve()));
}

test("real API failure is visible and retry recovers after restart", async ({ page }) => {
  test.skip(!runLiveIntegration, "Set RUN_LIVE_INTEGRATION=1 to run real-process integration.");

  let api = await startApi();
  try {
    await signIn(page);
    await expect(page.getByTestId("health-success")).toContainText("Connected to arizonix-api");

    await stopApi(api);
    await page.reload();
    await expect(page.getByTestId("health-error")).toContainText("could not be reached");

    api = await startApi();
    await page.getByRole("button", { name: "Retry connection" }).click();
    await expect(page.getByTestId("health-success")).toContainText("API version 0.1.0");
  } finally {
    await stopApi(api);
  }
});
