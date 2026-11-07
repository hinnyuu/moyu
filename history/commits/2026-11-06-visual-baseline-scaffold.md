---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: false
docs_reason: 截图基线文件尚未生成，文档将在基线生成后更新
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: npx playwright test --list; python3 -c "import yaml; yaml.safe_load(open('.github/workflows/visual-baseline.yml'))"; agent-gate --staged
---

# 主题截图基线脚手架

## 背景

发布前缺口：明暗主题截图基线。

## 改动

- Playwright 增加截图用例：登录、任务页亮色、任务页暗色。
- 基线缺失且未设置 `MOYU_UPDATE_SNAPSHOTS` 时跳过，避免基线生成前 CI 失败。
- 新增 `visual-baseline` workflow：
  - workflow_dispatch 或 push `visual-baseline` 分支触发；
  - 生成截图并提交到 main。

## 影响

- 基线生成后，截图用例开始参与回归。
- 本提交时尚无基线文件。

## 验证

- Playwright 列出 6 个用例。
- workflow YAML 解析通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
