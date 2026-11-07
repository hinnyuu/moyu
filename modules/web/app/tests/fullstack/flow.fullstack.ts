import { expect, test } from "@playwright/test";

const password = process.env.MOYU_E2E_PASSWORD || "e2e-secret-pass";
const bootstrap = process.env.MOYU_E2E_BOOTSTRAP || "e2e-boot-token";

test("real backend upload, pack and theme", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  await page.goto("/");
  expect(await page.evaluate(() => window.crossOriginIsolated)).toBe(true);
  await expect(page.getByRole("heading", { name: "moyu" })).toBeVisible();
  await page.locator("#bootstrap").fill(bootstrap);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: "初始化并登录" }).click();
  await expect(page.getByRole("button", { name: "任务" })).toBeVisible();

  await page.getByRole("button", { name: "上传", exact: true }).click();
  await page.locator("input[type=file]").setInputFiles({
    name: "frame.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGM4IScHAAK2AQU0pnWqAAAAAElFTkSuQmCC",
      "base64",
    ),
  });
  await expect(page.locator("tbody")).toContainText("frame.png");
  await page
    .locator("tbody tr")
    .first()
    .getByRole("button", { name: "上传", exact: true })
    .click();
  await expect(page.locator("tbody tr").first().locator(".badge")).toHaveText("done", {
    timeout: 30_000,
  });

  await expect(page.getByRole("heading", { name: "创建打包任务" })).toBeVisible();
  await page.locator("#asset").selectOption({ index: 1 });
  await page.getByRole("button", { name: "创建任务" }).click();
  await expect(page.locator(".success")).toContainText("已创建", { timeout: 20_000 });
  await page.getByRole("button", { name: "任务", exact: true }).click();
  await expect(page.locator("tbody .badge").first()).toHaveText("succeeded", {
    timeout: 40_000,
  });

  await page.getByRole("button", { name: /主题：/ }).click();
  await page.getByRole("button", { name: /主题：/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(errors).toEqual([]);
});
