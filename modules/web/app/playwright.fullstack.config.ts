import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig({
  ...base,
  testDir: "./tests/fullstack",
  testMatch: "**/*.fullstack.ts",
  webServer: undefined,
  use: {
    ...base.use,
    baseURL: process.env.MOYU_E2E_BASE_URL || "http://127.0.0.1:8800",
  },
});
