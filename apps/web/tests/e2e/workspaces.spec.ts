import { expect, test, type Page } from "@playwright/test";

import { signIn } from "./support/auth";

const apiBase = "http://127.0.0.1:8011/api/v1";
const firstId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const secondId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const userId = "1309ec68-70d6-47e8-9dc2-bd9d73177a84";

function workspace(id: string, name: string, role = "owner") {
  return {
    id,
    name,
    role,
    created_by: userId,
    created_at: "2026-09-28T00:00:00Z",
    updated_at: "2026-09-28T00:00:00Z",
  };
}

async function mockIdentity(page: Page) {
  await page.route(`${apiBase}/me`, (route) =>
    route.fulfill({ json: { user_id: userId, email: "analyst@example.com" } }),
  );
}

test("first-workspace onboarding creates once and selects the result", async ({ page }) => {
  let created = false;
  let posts = 0;
  await page.route(`${apiBase}/workspaces?limit=100`, (route) =>
    route.fulfill({
      json: {
        items: created ? [workspace(firstId, "Northstar")] : [],
        limit: 100,
        offset: 0,
        has_more: false,
      },
    }),
  );
  await page.route(`${apiBase}/workspaces`, async (route) => {
    posts += 1;
    created = true;
    await route.fulfill({ status: 201, json: workspace(firstId, "Northstar") });
  });

  await signIn(page);
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: "Create your first workspace" })).toBeVisible();
  await page.getByLabel("Workspace name").fill("Northstar");
  await page.getByRole("button", { name: "Create workspace", exact: true }).dblclick();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByLabel("Active workspace").first()).toHaveValue(firstId);
  expect(posts).toBe(1);
});

test("switching uses only accessible workspaces and survives responsive widths", async ({
  page,
}) => {
  await page.route(`${apiBase}/workspaces?limit=100`, (route) =>
    route.fulfill({
      json: {
        items: [workspace(firstId, "Northstar"), workspace(secondId, "Signal Lab", "viewer")],
        limit: 100,
        offset: 0,
        has_more: false,
      },
    }),
  );
  await signIn(page);
  const switcher = page.getByLabel("Active workspace").first();
  await switcher.selectOption(secondId);
  await expect(switcher).toHaveValue(secondId);
  expect(await page.evaluate(() => localStorage.getItem("arizonix.active-workspace.v1"))).toBe(
    secondId,
  );
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
        ),
      )
      .toBe(true);
  }
});

test("settings honor role controls and explain the last-owner failure", async ({ page }) => {
  await mockIdentity(page);
  await page.route(`${apiBase}/workspaces?limit=100`, (route) =>
    route.fulfill({
      json: {
        items: [workspace(firstId, "Northstar")],
        limit: 100,
        offset: 0,
        has_more: false,
      },
    }),
  );
  await page.route(`${apiBase}/workspaces/${firstId}/members?limit=100`, (route) =>
    route.fulfill({
      json: {
        items: [
          {
            user_id: userId,
            email: "analyst@example.com",
            role: "owner",
            created_at: "2026-09-28T00:00:00Z",
            updated_at: "2026-09-28T00:00:00Z",
          },
        ],
        limit: 100,
        offset: 0,
        has_more: false,
      },
    }),
  );
  await page.route(`${apiBase}/workspaces/${firstId}/members/${userId}`, (route) =>
    route.fulfill({
      status: 409,
      json: { detail: { code: "last_owner", message: "A workspace must keep one owner" } },
    }),
  );
  await signIn(page, "/settings");
  await expect(page.getByText("Your current role is")).toContainText("owner");
  await expect(page.getByText("Add an existing user by the exact ID")).toBeVisible();
  await page.getByLabel("Member role").selectOption("viewer");
  await expect(page.getByText(/Promote another member to owner/)).toBeVisible();

  await page.setViewportSize({ width: 375, height: 900 });
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    )
    .toBe(true);
});

test("sign-out clears the workspace preference", async ({ page }) => {
  await page.route(`${apiBase}/workspaces?limit=100`, (route) =>
    route.fulfill({
      json: {
        items: [workspace(firstId, "Northstar")],
        limit: 100,
        offset: 0,
        has_more: false,
      },
    }),
  );
  await signIn(page);
  await expect(page.getByLabel("Active workspace").first()).toHaveValue(firstId);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(
    await page.evaluate(() => localStorage.getItem("arizonix.active-workspace.v1")),
  ).toBeNull();
});
