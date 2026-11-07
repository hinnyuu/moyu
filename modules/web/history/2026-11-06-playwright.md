---
date: 2026-11-06
module: web
commit: (included in this commit)
---

# Playwright 前端 E2E

## 改动

- 新增 Playwright 配置与 3 个 mock E2E。
- CI 安装 Chromium 并运行 `npm run test:e2e`。

## 影响

- 覆盖登录、主题持久化、上传队列刷新恢复。
- 真实后端联动与视觉回归仍待补。
