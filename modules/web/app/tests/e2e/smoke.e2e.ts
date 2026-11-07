import fs from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

async function mockApi(page: Page, initiallyAuthenticated = false) {
  let authenticated = initiallyAuthenticated;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (path === "/api/v1/health") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", configured: true }),
      });
    }
    if (path === "/api/v1/auth/session" && method === "POST") {
      authenticated = true;
      return route.fulfill({ status: 204 });
    }
    if (path === "/api/v1/auth/session" && method === "GET") {
      if (!authenticated) {
        return route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({ code: "auth_required", message: "需要登录" }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          username: "admin",
          role: "admin",
          csrf: "csrf-token",
          expires_at: Math.floor(Date.now() / 1000) + 3600,
        }),
      });
    }
    if (path === "/api/v1/users" && method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { username: "admin", role: "admin", created_at: "2026-11-06T00:00:00Z" },
        ]),
      });
    }
    if (path === "/api/v1/jobs") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    }
    if (path === "/api/v1/config") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          global: {},
          modules: {},
          revisions: {},
          degraded: [],
        }),
      });
    }
    if (path === "/api/v1/uploads" && method === "POST") {
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: "s1", offset: 0, size: 9 }),
      });
    }
    if (path === "/api/v1/uploads/s1" && method === "PATCH") {
      return route.fulfill({
        status: 204,
        headers: { "Upload-Offset": "9" },
      });
    }
    if (path === "/api/v1/uploads/s1/finish") {
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "a1",
          original_name: "frame.bin",
          size: 9,
          sha256: "x",
          media_type: "application/octet-stream",
          created_at: "2026-11-06T00:00:00Z",
        }),
      });
    }
    if (path.includes("/previews/")) {
      return route.fulfill({ status: 404, body: "no preview" });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ code: "not_found", message: "mock" }),
    });
  });
  return () => authenticated;
}

test("login flow", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "moyu" })).toBeVisible();
  await page.locator("#password").fill("secret-pass");
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page.getByRole("button", { name: "任务" })).toBeVisible();
});

test("login and jobs meet WCAG AA", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  const login = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .disableRules(["region"])
    .analyze();
  expect(summarize(login.violations)).toEqual([]);

  await page.locator("#password").fill("secret-pass");
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page.getByRole("button", { name: "任务", exact: true })).toBeVisible();
  const jobs = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .disableRules(["region"])
    .analyze();
  expect(summarize(jobs.violations)).toEqual([]);

  await page.getByRole("button", { name: /主题：/ }).click();
  await page.getByRole("button", { name: /主题：/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const dark = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .disableRules(["region"])
    .analyze();
  expect(summarize(dark.violations)).toEqual([]);
});

function summarize(violations: Array<{ id: string; nodes: Array<{ target: string[] }> }>) {
  return violations.map((violation) => ({
    id: violation.id,
    targets: violation.nodes.map((node) => node.target.join(" ")),
  }));
}

test("admin can open users page", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.locator("#password").fill("secret-pass");
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page.getByRole("button", { name: "任务", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "用户", exact: true }).click();
  await expect(page.getByRole("heading", { name: "用户" })).toBeVisible();
  await expect(page.locator("tbody")).toContainText("admin");
});

test("theme persists without flash", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("moyu-theme", "dark"));
  await mockApi(page);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(errors).toEqual([]);
});

test("theme screenshots", async ({ page }, testInfo) => {
  const baseline = testInfo.snapshotPath("login-light.png");
  test.skip(
    !fs.existsSync(baseline) && !process.env.MOYU_UPDATE_SNAPSHOTS,
    "截图基线尚未生成",
  );
  await mockApi(page);
  await page.goto("/");
  await expect(page).toHaveScreenshot("login-light.png");
  await page.locator("#password").fill("secret-pass");
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page.getByRole("button", { name: "任务", exact: true })).toBeVisible();
  await expect(page).toHaveScreenshot("jobs-light.png");
  await page.getByRole("button", { name: /主题：/ }).click();
  await page.getByRole("button", { name: /主题：/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page).toHaveScreenshot("jobs-dark.png");
});

test("upload queue survives reload", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("moyu-theme", "light"));
  await mockApi(page, true);
  await page.goto("/");
  await page.getByRole("button", { name: "上传", exact: true }).click();
  await page.locator("input[type=file]").setInputFiles({
    name: "frame.bin",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("123456789"),
  });
  await expect(page.locator("tbody")).toContainText("frame.bin");
  await page.locator("tbody tr").first().getByRole("button", { name: "上传", exact: true }).click();
  await expect(page.locator("tbody tr").first().locator(".badge")).toHaveText("done");
  await page.reload();
  await page.getByRole("button", { name: "上传", exact: true }).click();
  await expect(page.locator("tbody")).toContainText("frame.bin");
});
