import { spawn, type ChildProcess } from "node:child_process";
import path from "node:path";

async function waitUntilReady(child: ChildProcess, url: string, label: string): Promise<void> {
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`${label} stopped during startup.`);
    try {
      if ((await fetch(url, { redirect: "manual" })).status < 500) return;
    } catch {
      // The server has not bound its port yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out while starting ${label}.`);
}

async function stopProcessTree(child: ChildProcess): Promise<void> {
  if (child.exitCode !== null || child.pid === undefined) return;
  if (process.platform === "win32") {
    const killer = spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
    await new Promise<void>((resolve) => killer.once("exit", () => resolve()));
    return;
  }
  process.kill(-child.pid, "SIGTERM");
  await new Promise<void>((resolve) => setTimeout(resolve, 250));
}

export default async function globalSetup(): Promise<() => Promise<void>> {
  const root = process.cwd();
  const mockScript = path.resolve(root, "tests/e2e/support/mock-supabase-server.mjs");
  const mock = spawn(process.execPath, [mockScript], {
    detached: process.platform !== "win32",
    stdio: "ignore",
  });
  await waitUntilReady(mock, "http://127.0.0.1:54321/health", "the mock Supabase server");

  const invalidConfig = process.env.EXPECT_INVALID_PUBLIC_CONFIG === "1";
  const apiUrl = invalidConfig
    ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1")
    : "http://127.0.0.1:8011";
  const nextCli = path.resolve(root, "node_modules/next/dist/bin/next");
  const web = spawn(
    process.execPath,
    [nextCli, "dev", "--hostname", "127.0.0.1", "--port", "3100"],
    {
      detached: process.platform !== "win32",
      stdio: "ignore",
      env: {
        ...process.env,
        NEXT_PUBLIC_API_BASE_URL: apiUrl,
        NEXT_PUBLIC_SITE_URL: "http://127.0.0.1:3100",
        NEXT_PUBLIC_SUPABASE_URL: "http://127.0.0.1:54321",
        NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_test",
      },
    },
  );
  await waitUntilReady(web, "http://127.0.0.1:3100/login", "the Next.js test server");

  return async () => {
    await stopProcessTree(web);
    await stopProcessTree(mock);
  };
}
