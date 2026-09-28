import { expect, test } from "@playwright/test";

import { signIn } from "./support/auth";

const expectInvalidConfiguration = process.env.EXPECT_INVALID_PUBLIC_CONFIG === "1";

test("invalid public API configuration shows corrective guidance", async ({ page }) => {
  test.skip(
    !expectInvalidConfiguration,
    "Set EXPECT_INVALID_PUBLIC_CONFIG=1 with an invalid public API URL to run this check.",
  );

  await signIn(page);
  await expect(page.getByTestId("health-error")).toContainText("public API URL must be an origin");
  await expect(page.getByRole("button", { name: "Retry connection" })).toBeVisible();
});
