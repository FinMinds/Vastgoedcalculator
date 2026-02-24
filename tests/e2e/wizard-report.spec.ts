import { test, expect } from "@playwright/test";

test("wizard to report flow", async ({ page }) => {
  await page.goto("http://localhost:3000");
  await page.getByRole("button", { name: "Step 5: Review & Analyze" }).click();
  await expect(page.getByText("KPI Cards")).toBeVisible();
  await expect(page.getByRole("link", { name: "Download deterministic PDF" })).toBeVisible();
});
