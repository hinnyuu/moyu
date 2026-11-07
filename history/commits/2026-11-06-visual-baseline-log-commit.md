---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules: []
docs_impact: false
docs_reason: 仅 CI 失败日志提交，不改变文档事实
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: python3 -c "import yaml; yaml.safe_load(open('.github/workflows/visual-baseline.yml'))"; agent-gate --staged
---

# 截图基线失败日志落盘

## 背景

visual-baseline 连续失败，但公开日志不可读。

## 改动

- 失败时把 `/tmp/playwright.log` 提交为 `baseline-error.log`。

## 影响

- 便于诊断 Playwright 失败原因。
