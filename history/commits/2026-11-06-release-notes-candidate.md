---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules: []
docs_impact: true
wiki_impact: false
wiki_reason: 发布说明是 docs 当前事实，不改变操作教程
breaking: false
tests: agent-gate --staged
---

# v0.0.1 发布说明候选

## 背景

发布前需要把范围、验证矩阵和已知限制集中成一份可审阅文档。

## 改动

- 新增 `docs/releases/v0.0.1.md`。
- README 链接发布候选说明。

## 影响

- 标签前可据此确认是否接受已知限制。
- 尚未创建标签。

## 验证

- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
