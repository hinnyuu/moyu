---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: true
wiki_impact: false
wiki_reason: E2E 属于测试与 CI，不改变用户操作教程
breaking: false
tests: npm run typecheck; npm test; npm run build; agent-gate --staged
---

# Playwright 前端 E2E

## 背景

发布清单要求 Playwright；此前只有 Vitest 队列单测，没有页面级验证。

## 改动

- 新增 `playwright.config.ts`，用 `vite preview` 提供构建产物。
- 新增 3 个 mock E2E：
  - 登录；
  - 深色主题持久化且无 pageerror；
  - 上传队列刷新后恢复。
- `web` workflow 增加 Playwright Chromium 安装与 `npm run test:e2e`。
- 忽略 `test-results/`、`playwright-report/`。
- 更新 Web/testing/release checklist 文档。

## 影响

- E2E 使用 mock API，不依赖后端；CI 可验证页面与队列状态。
- 真实后端联动、主题截图基线与对比度自动检查仍未接入。

## 验证

- `npm run typecheck`、`npm test`、`npm run build` 通过。
- 本地未安装 Chromium，未运行 `test:e2e`；待 `web` workflow 验证。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
