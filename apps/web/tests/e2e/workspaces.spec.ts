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

test("owner can filter and paginate audit history without horizontal overflow", async ({
  page,
}) => {
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
  const event = (id: string, action = "workspace.renamed") => ({
    id,
    workspace_id: firstId,
    actor_user_id: userId,
    action,
    target_type: "workspace",
    target_id: firstId,
    occurred_at: "2026-10-03T08:30:00Z",
    request_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    event_schema_version: 1,
    details: { previous_name: "Northstar", new_name: "Signal Lab" },
  });
  const firstEventId = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
  const secondEventId = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
  await page.route(`**/workspaces/${firstId}/audit-events?*`, (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.has("cursor")) {
      return route.fulfill({ json: { items: [event(secondEventId)], next_cursor: null } });
    }
    if (url.searchParams.get("action") === "membership.added") {
      return route.fulfill({ json: { items: [], next_cursor: null } });
    }
    return route.fulfill({ json: { items: [event(firstEventId)], next_cursor: "next" } });
  });

  await signIn(page, "/settings/audit");
  await expect(page.getByRole("heading", { name: "Audit history" })).toBeVisible();
  await expect(page.getByText("Renamed the workspace")).toBeVisible();
  await page.getByText("Event details").click();
  await expect(page.getByText(firstEventId)).toBeVisible();
  await page.getByRole("button", { name: "Load more" }).click();
  await expect(page.getByText("Renamed the workspace")).toHaveCount(2);
  await page.getByLabel("Action").selectOption("membership.added");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByText("No events match these filters.")).toBeVisible();

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

test("viewer direct audit navigation is denied without fetching history", async ({ page }) => {
  await mockIdentity(page);
  await page.route(`${apiBase}/workspaces?limit=100`, (route) =>
    route.fulfill({
      json: {
        items: [workspace(firstId, "Northstar", "viewer")],
        limit: 100,
        offset: 0,
        has_more: false,
      },
    }),
  );
  let auditRequests = 0;
  await page.route(`**/workspaces/${firstId}/audit-events?*`, (route) => {
    auditRequests += 1;
    return route.fulfill({ status: 403, json: { detail: { code: "permission_denied" } } });
  });

  await signIn(page, "/settings/audit");
  await expect(page.getByText(/available only to workspace owners and admins/)).toBeVisible();
  expect(auditRequests).toBe(0);
});
