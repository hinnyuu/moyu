---
date: 2026-11-06
module: agent-gate
commit: (included in this commit)
---

# 修复 PR 检查 checkout 目标

## 背景

GitHub PR 的 `pull_request` 事件默认 checkout 临时 merge commit，导致 agent-gate 把没有 history 的合成提交当成项目提交，CI 误报。

## 改动

- workflow 在 PR 中 checkout `github.event.pull_request.head.sha`。
- push 事件继续使用 `github.ref`。
- 同时指定 PR head repo，兼容同仓库/分支场景。
- 更新模块 docs/wiki。

## 影响

- PR 只检查真实 PR head 提交。
- push 行为不变。
