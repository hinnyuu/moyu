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
tests: python3 -m unittest discover -s modules/agent-gate/tests -v; agent-gate --staged
---

# 发布前文档二轮校对与发布清单

## 背景

第一轮只修了明显的“尚未实现”。继续审计发现架构/测试/契约仍保留草稿口径和未实现能力描述。

## 改动

- 架构 modules/overview：去掉“草稿”，更新 preview/wasm/deploy 能力、`moyu-core` 命名、Web 手写客户端说明。
- testing：区分已接入 CI 与未接入项（cargo deny、Playwright、ZIP64/大文件、aarch64）。
- contracts README：HTTP API 指向 OpenAPI；版本状态更新。
- module-interfaces：WASM 产物与 Web 懒加载现状。
- wiki/getting-started：api 注释去除内置预览。
- agent-gate/contracts wiki、wasm-client README 状态。
- 新增 `docs/development/release-checklist.md`，关联升级/回滚 wiki。

## 影响

- 文档不再把已实现能力标成未来项，也不把未实现项说成已完成。
- 发布清单明确列出已知未完成项，要求写进 Release notes。

## 验证

- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
