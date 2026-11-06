---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - docs
  - agent-gate
docs_impact: true
wiki_impact: true
breaking: false
tests: 6 agent-gate unit tests; local gate; GitHub main workflow rerun
---

# 修复 agent-gate 空范围与 merge commit

## 背景

PR 合并后 main workflow 失败：`origin/main..HEAD` 为空，agent-gate 将其误报为“没有提交”；同时 GitHub PR merge commit 没有 history。

## 改动

- 空范围通过。
- 跳过 merge commit 的 history 检查。
- push workflow 使用 `github.event.before` 作为 base。
- 增加空范围测试，更新 docs/wiki/history。

## 影响

- main 合并后不再误报。
- PR head 的真实提交仍逐个检查。
- 直接 push 到 main 的非合并提交仍会被检查。

## 验证

- 本地 6 个 agent-gate 单元测试通过。
- 本地 `agent-gate check --base origin/main` 通过。
- 推送后观察 GitHub main workflow。
