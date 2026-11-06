---
date: 2026-11-06
branch: draft/v0.0.1-architecture
commit: (included in this commit)
modules:
  - docs
  - agent-gate
docs_impact: true
wiki_impact: true
breaking: false
tests: local agent-gate tests; local gate check; GitHub PR workflow rerun
---

# 修复 agent-gate PR checkout

## 背景

PR 运行失败：GitHub checkout 的是临时 merge commit `378a5bd`，它没有 history/commits 记录，agent-gate 误报。

## 改动

- `.github/workflows/agent-gate.yml`：PR 时 checkout `pull_request.head.sha` 和 head repo；push 保持 `github.ref`。
- 更新 agent-gate 模块 docs、wiki、history。

## 影响

- PR 只检查真实 PR head 提交，不检查 GitHub 合成 merge commit。
- 后续 PR 的 agent-gate 应能通过。

## 验证

- 本地 agent-gate 单元测试通过。
- 本地 `agent-gate check --base origin/main` 通过。
- 推送后重新观察 GitHub PR workflow。
