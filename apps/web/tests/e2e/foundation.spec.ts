import { expect, test } from "@playwright/test";

import { signIn } from "./support/auth";

const healthUrl = "http://127.0.0.1:8011/api/v1/health";

test("shell renders and every navigation destination resolves", async ({ page }) => {
  await page.route(healthUrl, (route) =>
    route.fulfill({ json: { status: "ok", service: "arizonix-api", version: "0.1.0" } }),
  );
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Research overview" })).toBeVisible();

  const destinations = [
    ["Prospects", "/prospects", "Prospects"],
    ["Research", "/research", "Research"],
    ["Evidence", "/evidence", "Evidence"],
    ["Human Review", "/review", "Human Review"],
    ["Settings", "/settings", "Settings"],
    ["Overview", "/", "Research overview"],
  ] as const;

  for (const [label, path, heading] of destinations) {
    await page.getByRole("link", { name: label, exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`${path === "/" ? "/$" : `${path}$`}`));
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }
});

test("health card accepts only the expected contract", async ({ page }) => {
  await page.route(healthUrl, (route) =>
    route.fulfill({ json: { status: "ok", service: "arizonix-api", version: "0.1.0" } }),
  );
  await signIn(page);
  await expect(page.getByTestId("health-success")).toContainText("Connected to arizonix-api");

  await page.unroute(healthUrl);
  await page.route(healthUrl, (route) =>
    route.fulfill({ json: { status: "ok", service: "wrong-service", version: "0.1.0" } }),
  );
  await page.reload();
  await expect(page.getByTestId("health-error")).toContainText("response was not recognized");
});

test("unavailable API shows an error and retry recovers", async ({ page }) => {
  let attempt = 0;
  await page.route(healthUrl, (route) => {
    attempt += 1;
    if (attempt === 1) return route.abort("connectionrefused");
    return route.fulfill({ json: { status: "ok", service: "arizonix-api", version: "0.1.0" } });
  });
  await signIn(page);
  await expect(page.getByTestId("health-error")).toContainText("could not be reached");
  await page.getByRole("button", { name: "Retry connection" }).click();
  await expect(page.getByTestId("health-success")).toBeVisible();
  expect(attempt).toBe(2);
});

test("mobile navigation is keyboard usable and layout does not overflow", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.route(healthUrl, (route) => route.abort("connectionrefused"));
  await signIn(page);
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    )
    .toBe(true);

  const menu = page.getByRole("button", { name: "Menu" });
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("dialog", { name: "Primary navigation" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menu).toBeFocused();

  await menu.click();
  await page.getByRole("link", { name: "Prospects", exact: true }).click();
  await expect(page).toHaveURL(/\/prospects$/);
  await expect(page.getByRole("dialog", { name: "Primary navigation" })).toBeHidden();
});

test("responsive shell has no page overflow at target widths", async ({ page }, testInfo) => {
  await page.route(healthUrl, (route) =>
    route.fulfill({ json: { status: "ok", service: "arizonix-api", version: "0.1.0" } }),
  );

  await signIn(page);

  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
        ),
      )
      .toBe(true);
    await expect(page.getByRole("heading", { name: "Research overview" })).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath(`overview-${width}.png`),
      fullPage: true,
    });

    if (width < 1024) {
      await expect(page.getByRole("button", { name: "Menu" })).toBeVisible();
    } else {
      await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
    }
  }
});
