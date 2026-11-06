---
date: 2026-11-06
module: agent-gate
commit: (included in this commit)
---

# 修复空范围与 merge commit 检查

## 背景

PR 合并后，main 上的 workflow 以 `origin/main..HEAD` 检查，范围为 0，被错误报告为“没有提交”。同时 GitHub 生成的 PR merge commit 没有 history。

## 改动

- 空提交范围视为正常，不报错。
- 跳过具有多个父提交的 merge commit。
- push workflow 使用 `github.event.before` 作为 base。
- 增加空范围单元测试。
- 更新模块 docs/wiki。

## 影响

- main 合并后的 workflow 不再误报。
- PR head 的真实提交仍逐个检查。
- 非合并的直接提交仍会被检查。
