---
date: 2026-11-06
module: web
commit: (included in this commit)
---

# 修复 Playwright/Vitest 文件冲突

## 改动

- Playwright 用例改为 `*.e2e.ts`，配置 testMatch。

## 影响

- Vitest 不再误执行 Playwright 文件。
