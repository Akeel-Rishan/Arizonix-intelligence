import type { Page } from "@playwright/test";

export async function signIn(page: Page, destination = "/"): Promise<void> {
  await page.goto(`/login?next=${encodeURIComponent(destination)}`);
  await page.getByLabel("Email address").fill("analyst@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(new RegExp(`${destination === "/" ? "/$" : `${destination}$`}`));
}
