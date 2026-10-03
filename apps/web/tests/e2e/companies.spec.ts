import { expect, test, type Page } from "@playwright/test";

import { signIn } from "./support/auth";

const apiBase = "http://127.0.0.1:8011/api/v1";
const workspaceId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const companyId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const userId = "1309ec68-70d6-47e8-9dc2-bd9d73177a84";

function workspace(role: "owner" | "viewer" = "owner") {
  return {
    id: workspaceId,
    name: "Northstar",
    role,
    created_by: userId,
    created_at: "2026-10-03T08:00:00Z",
    updated_at: "2026-10-03T08:00:00Z",
  };
}

function company(overrides = {}) {
  return {
    id: companyId,
    workspace_id: workspaceId,
    name: "Acme Logistics",
    website_url: "https://example.test",
    industry: "Logistics",
    country_code: "LK",
    description: "A manually entered prospect.",
    notes: "Contact after qualification.",
    created_by: userId,
    updated_by: userId,
    created_at: "2026-10-03T08:00:00Z",
    updated_at: "2026-10-03T08:00:00Z",
    archived_at: null,
    archived_by: null,
    version: 1,
    ...overrides,
  };
}

async function mockWorkspace(page: Page, role: "owner" | "viewer" = "owner") {
  await page.route(`${apiBase}/workspaces?limit=100`, (route) =>
    route.fulfill({
      json: { items: [workspace(role)], limit: 100, offset: 0, has_more: false },
    }),
  );
}

test("company list keeps filters in the URL, paginates, and remains responsive", async ({
  page,
}) => {
  await mockWorkspace(page);
  const seenQueries: URLSearchParams[] = [];
  await page.route(`**/workspaces/${workspaceId}/companies?*`, (route) => {
    const query = new URL(route.request().url()).searchParams;
    seenQueries.push(query);
    return route.fulfill({
      json: {
        items: [company({ notes: undefined })],
        next_cursor: query.has("cursor") ? null : "next-page",
      },
    });
  });
  await signIn(page, "/prospects");
  await expect(page.getByText("Acme Logistics")).toBeVisible();
  await page.getByLabel("Search").fill("Acme");
  await expect(page).toHaveURL(/search=Acme/);
  await expect.poll(() => seenQueries.some((query) => query.get("search") === "Acme")).toBe(true);
  await page.getByLabel("Status").selectOption("all");
  await expect(page).toHaveURL(/archive=all/);
  await page.getByRole("button", { name: "Load more" }).click();
  await expect.poll(() => seenQueries.some((query) => query.has("cursor"))).toBe(true);

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

test("editor creates a company and archive uses the current version", async ({ page }) => {
  await mockWorkspace(page);
  let postedBody: unknown;
  await page.route(`${apiBase}/workspaces/${workspaceId}/companies`, async (route) => {
    postedBody = route.request().postDataJSON();
    await route.fulfill({ status: 201, json: company() });
  });
  await page.route(`${apiBase}/workspaces/${workspaceId}/companies/${companyId}`, (route) =>
    route.fulfill({ json: company() }),
  );
  let archiveBody: unknown;
  await page.route(
    `${apiBase}/workspaces/${workspaceId}/companies/${companyId}/archive`,
    async (route) => {
      archiveBody = route.request().postDataJSON();
      await route.fulfill({ json: company({ archived_at: "2026-10-03T09:00:00Z", version: 2 }) });
    },
  );
  await page.route(`${apiBase}/workspaces/${workspaceId}/companies/${companyId}/restore`, (route) =>
    route.fulfill({
      json: company({ archived_at: null, archived_by: null, version: 3 }),
    }),
  );

  await signIn(page, "/prospects/new");
  await page.getByLabel(/Company name/).fill("Acme Logistics");
  await page.getByLabel("Website").fill("https://example.test");
  await page.getByLabel("Country code").fill("lk");
  await page.getByRole("button", { name: "Create company" }).click();
  await expect(page).toHaveURL(new RegExp(`/prospects/${companyId}$`));
  expect(postedBody).toMatchObject({
    name: "Acme Logistics",
    website_url: "https://example.test",
    country_code: "LK",
  });
  await page.getByRole("button", { name: "Archive", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Archive" }).click();
  await expect(page.getByText("Archived", { exact: true })).toBeVisible();
  expect(archiveBody).toEqual({ expected_version: 1 });
  await page.getByRole("button", { name: "Restore", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Restore" }).click();
  await expect(page.getByText("Archived", { exact: true })).toHaveCount(0);
});

test("stale edit preserves input and offers a confirmed reload", async ({ page }) => {
  await mockWorkspace(page);
  await page.route(`${apiBase}/workspaces/${workspaceId}/companies/${companyId}`, (route) => {
    if (route.request().method() === "PATCH") {
      return route.fulfill({
        status: 409,
        json: {
          detail: {
            code: "version_conflict",
            message: "This company changed since you opened it. Refresh and try again",
          },
        },
      });
    }
    return route.fulfill({ json: company() });
  });
  await signIn(page, `/prospects/${companyId}/edit`);
  const name = page.getByLabel(/Company name/);
  await name.fill("Unsaved local name");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText(/This company changed since you opened it/)).toBeVisible();
  await expect(name).toHaveValue("Unsaved local name");
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Reload latest company" }).click();
});

test("viewer sees company details without mutation controls", async ({ page }) => {
  await mockWorkspace(page, "viewer");
  await page.route(`${apiBase}/workspaces/${workspaceId}/companies/${companyId}`, (route) =>
    route.fulfill({ json: company() }),
  );
  await signIn(page, `/prospects/${companyId}`);
  await expect(page.getByRole("heading", { name: "Acme Logistics" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Edit" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Archive" })).toHaveCount(0);
});
