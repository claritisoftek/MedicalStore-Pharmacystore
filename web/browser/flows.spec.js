import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
test("Counter, print receipt, admin forms, responsive layout and logout", async ({
  page,
  context,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("Admin");
  await page.getByLabel("Password", { exact: true }).fill("test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "A little care. A better day." }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Administration", exact: true })
    .click();
  await page.getByRole("button", { name: "Company profile & logo" }).click();
  await page
    .getByLabel("Replace logo (PNG / JPEG, max 5 MB)")
    .setInputFiles("assets/company-default.png");
  await page.getByLabel("Company name", { exact: true }).fill("Your Pharmacy");
  await page
    .getByLabel("Tagline", { exact: true })
    .fill("Your health, our care");
  await page.getByRole("button", { name: "Save company profile" }).click();
  await expect(page.locator("#modal")).not.toBeVisible();
  await page.getByRole("button", { name: "Counter", exact: true }).click();
  await page.locator("#search").fill("IMPORTED");
  await page.getByRole("button", { name: "+ Add", exact: true }).click();
  await expect(page.locator("#cart-lines")).toContainText("Imported medicine");
  await page.getByLabel("Cash received (PKR)", { exact: true }).fill("100");
  await expect(page.locator("#change")).toContainText("90.00 change");
  await mkdir("web/test-output/screenshots", { recursive: true });
  await expect(page.locator("#notices")).toHaveText("", { timeout: 8000 });
  await page.screenshot({
    path: "web/test-output/screenshots/counter-desktop.png",
    fullPage: true,
  });
  const beforeSales = (await (await page.request.get("/api/state")).json())
    .sales.length;
  let interrupted = false;
  await page.route("**/api/sales", async (route) => {
    if (!interrupted) {
      interrupted = true;
      await route.fetch();
      await route.fulfill({
        status: 502,
        contentType: "text/html",
        body: "Upstream interrupted",
      });
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Complete sale" }).click();
  await expect(page.locator("#checkout-error")).toContainText("interrupted");
  await page.getByRole("button", { name: "Complete sale" }).click();
  await expect(
    page.getByRole("heading", { name: "Sales", exact: true }),
  ).toBeVisible();
  expect(
    (await (await page.request.get("/api/state")).json()).sales.length,
  ).toBe(beforeSales + 1);
  await page.unroute("**/api/sales");
  await expect(
    page.getByRole("heading", { name: "Sales", exact: true }),
  ).toBeVisible();
  const receiptPromise = context.waitForEvent("page");
  await page.getByRole("link", { name: "Print", exact: true }).first().click();
  const receipt = await receiptPromise;
  await expect(
    receipt.getByRole("heading", { name: "Customer receipt" }),
  ).toBeVisible();
  await receipt.close();
  await page
    .getByRole("button", { name: "Administration", exact: true })
    .click();
  await page.getByRole("button", { name: "Company profile & logo" }).click();
  await expect(
    page.getByRole("heading", { name: "Company profile", exact: true }),
  ).toBeVisible();
  await expect(page.locator("#notices")).toHaveText("", { timeout: 8000 });
  await page.screenshot({
    path: "web/test-output/screenshots/company-profile.png",
  });
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.getByRole("button", { name: "Purchases", exact: true }).click();
  await page.getByRole("button", { name: "New vendor bill" }).click();
  await page.getByLabel("Vendor bill reference").fill("UI-PREVIEW");
  await page.getByLabel("Batch", { exact: true }).fill("UI-BATCH");
  await page.getByLabel("Expiry", { exact: true }).fill("2099-01-01");
  await page.getByRole("button", { name: "Add batch to bill" }).click();
  await expect(page.locator("#purchase-lines")).toContainText("UI-BATCH");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.getByRole("button", { name: "Reports", exact: true }).click();
  await page.getByRole("button", { name: "Generate report" }).click();
  await expect(page.locator("#report-result")).toContainText("Sales revenue");
  await page.getByRole("button", { name: "Counter", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("button", { name: "+ Add", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("link", { name: "Review sale (1)" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Review sale (1)" }).click();
  await page.getByLabel("Cash received (PKR)", { exact: true }).fill("20");
  await expect(page.locator("#change")).toContainText("10.00 change");

  await expect(page.locator("#notices")).toHaveText("", { timeout: 8000 });
  await page.screenshot({
    path: "web/test-output/screenshots/counter-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
