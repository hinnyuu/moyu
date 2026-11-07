---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules: []
docs_impact: false
docs_reason: 仅新增 CI 诊断输出，文档事实不变
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: python3 -c "import yaml; yaml.safe_load(open('.github/workflows/visual-baseline.yml'))"; agent-gate --staged
---

# 截图基线生成诊断

## 背景

visual-baseline Generate baselines 连续失败，但日志不可公开读取。

## 改动

- 将 Playwright 输出写入 `$GITHUB_STEP_SUMMARY`，失败时可在运行页面看到。

## 影响

- 仅诊断信息，不改变基线生成行为。
