---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - agent-gate
  - contracts
  - wasm-client
docs_impact: true
wiki_impact: true
breaking: false
tests: agent-gate --staged
---

# 发布前文档状态第一轮校对

## 背景

发布前审计发现根入口、入门 wiki 和三个模块仍把“已实现”写成“架构草稿/尚未实现”，与实际代码和 CI 不符。

## 改动

- 根 README：移除“draft 分支、无业务实现”，改为当前实现与待补清单。
- AGENTS：说明架构已合并到 main、实现直接在 main 提交；解释 `status: draft` 表示未发布而非未实现。
- wiki/getting-started：更新为可运行状态，并区分当前三容器与目标五容器。
- agent-gate、contracts、wasm-client 的 README/docs 状态更新。
- 修复 runtime-topology 中的乱码字符。

## 影响

- 文档第一轮不再声称“没有可运行实现”。
- 仍未完成逐段全量校对；待计划功能补齐后继续。

## 验证

- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
