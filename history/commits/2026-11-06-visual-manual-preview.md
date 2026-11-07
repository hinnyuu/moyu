---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: false
docs_reason: 仅修复截图生成的本地 preview 启动方式
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: npx playwright test --list; python3 -c "import yaml; yaml.safe_load(open('.github/workflows/visual-baseline.yml'))"; agent-gate --staged
---

# 截图基线改为手动启动 preview

## 背景

Playwright webServer 在 visual-baseline 中反复超时，而 web CI 同一配置正常。

## 改动

- `playwright.config.ts` 支持 `MOYU_E2E_NO_WEBSERVER=1` 禁用内建 webServer。
- visual-baseline 手动启动 `vite preview`，等待端口后再运行 Playwright。
- 失败日志包含 preview 输出。

## 影响

- 绕过 webServer 超时；preview 启动失败会明确记录。
