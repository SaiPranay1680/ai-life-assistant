import { expect, test } from "@playwright/test";

test("login page renders its primary sign-in flow", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByLabel("Email address").fill("test@example.com");
  await page.getByLabel("Password").fill("password123");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Forgot password?" })).toBeVisible();
});
