import { expect, test } from "@playwright/test";

import { signIn } from "./support/auth";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:54321/test/reset");
});

test("protected routes redirect to sign-in and preserve a safe destination", async ({ page }) => {
  await page.goto("/evidence?view=recent");
  await expect(page).toHaveURL(/\/login\?next=%2Fevidence%3Fview%3Drecent/);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence" })).toBeHidden();

  await page.goto("/login?next=https://attacker.example");
  await page.getByLabel("Email address").fill("analyst@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/$/);
});

test("sign-in validates, reports generic failures, succeeds, and signs out", async ({ page }) => {
  await page.goto("/login?next=%2Fsettings");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Enter a valid email address.")).toBeVisible();
  await expect(page.getByText("Password must be at least 8 characters.")).toBeVisible();

  await page.getByLabel("Email address").fill("analyst@example.com");
  await page.getByLabel("Password", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Email or password is incorrect.", { exact: true })).toBeVisible();

  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/settings");
  await expect(page).toHaveURL(/\/login\?next=%2Fsettings/);
});

test("sign-up validates matching passwords and submits only once while pending", async ({
  page,
  request,
}) => {
  await page.goto("/signup");
  await page.getByLabel("Email address").fill("new@example.com");
  await page.getByLabel("Password", { exact: true }).fill("long-password");
  await page.getByLabel("Confirm password").fill("different-password");
  await expect(page.getByText("Passwords do not match.")).toBeVisible();

  await page.getByLabel("Confirm password").fill("long-password");
  const submit = page.getByRole("button", { name: "Create account" });
  await submit.dblclick();
  await expect(page).toHaveURL(/\/check-email\?email=new%40example.com/);
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
  const counts = await (await request.get("http://127.0.0.1:54321/test/counts")).json();
  expect(counts.signup).toBe(1);
});

test("expired confirmation is token-free and mobile auth layout does not overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/auth/confirm?token_hash=expired&type=email&next=%2Fsettings");
  await expect(page).toHaveURL(/\/login\?confirmation=expired$/);
  await expect(page.getByText(/confirmation link is invalid or expired/)).toBeVisible();
  expect(page.url()).not.toContain("token_hash");
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    )
    .toBe(true);
  for (const width of [768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
        ),
      )
      .toBe(true);
  }
});

test("a valid session can navigate every protected route", async ({ page }) => {
  await signIn(page, "/research");
  await expect(page.getByRole("heading", { name: "Research", exact: true })).toBeVisible();
  await page.goto("/review");
  await expect(page.getByRole("heading", { name: "Human Review", exact: true })).toBeVisible();
});

test("a valid email confirmation establishes the session and uses the safe destination", async ({
  page,
}) => {
  await page.goto("/auth/confirm?token_hash=valid-token&type=email&next=%2Fsettings");
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  expect(page.url()).not.toContain("token_hash");
});

test("the API client refreshes once on 401 and distinguishes verification outages", async ({
  page,
}) => {
  const meUrl = "http://127.0.0.1:8011/api/v1/me";
  let attempts = 0;
  await page.route(meUrl, (route) => {
    attempts += 1;
    if (attempts === 1)
      return route.fulfill({ status: 401, json: { detail: "Invalid access token" } });
    return route.fulfill({
      json: { user_id: "1309ec68-70d6-47e8-9dc2-bd9d73177a84", email: "analyst@example.com" },
    });
  });
  await signIn(page, "/settings");
  await expect(page.getByText("1309ec68-70d6-47e8-9dc2-bd9d73177a84")).toBeVisible();
  expect(attempts).toBe(2);

  await page.unroute(meUrl);
  await page.route(meUrl, (route) => route.fulfill({ status: 503 }));
  await page.reload();
  await expect(
    page.getByText("Authentication verification is unavailable on the API."),
  ).toBeVisible();
});
