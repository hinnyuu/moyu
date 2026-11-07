---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: false
docs_reason: 仅修复截图生成命令与 webServer 超时
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: npx playwright test --list; python3 -c "import yaml; yaml.safe_load(open('.github/workflows/visual-baseline.yml'))"; agent-gate --staged
---

# 修复截图基线 webServer 超时

## 背景

失败日志显示 `Timed out waiting 30000ms from config.webServer`。

## 改动

- visual-baseline 使用 `npm run test:e2e -- ...`（本地 Playwright），不再 `npx playwright`。
- Playwright webServer 超时提升到 60 秒。

## 影响

- 基线生成使用与 web CI 相同的启动方式。
