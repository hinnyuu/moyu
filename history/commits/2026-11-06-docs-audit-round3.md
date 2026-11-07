---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - contracts
  - deploy
docs_impact: true
wiki_impact: true
breaking: false
tests: agent-gate --staged
---

# 发布前文档三轮校对

## 背景

继续逐段审计发现部署草稿口径、旧预览路径、wasm-pack 命令、GHCR 未实现说明等仍与代码不一致。

## 改动

- 去除 architecture/contracts/operations/rust-workspace 标题中的“草稿”。
- 修正 `/data/preview`、`/data/state.db`、`config/state/audit.db` 路径。
- 修正 wiki 中“preview 内置/tusd 未接入/视频 EXR 未启用”等过期描述。
- 修正容器数量“三容器”为实际角色列表。
- rust-workspace 命令改为实际 crate 名与 wasm-bindgen CLI；移除未接入的 cargo deny/audit。
- deploy docs 移除“GHCR 未实现”，说明 release/arm64 实际状态。
- release checklist/testing 标注 >65535 已覆盖，>4GiB 与重启续传仍未覆盖。

## 影响

- 文档与当前五容器、预览/发布实现一致。
- 剩余限制仍明确列出：WASM 转码、>4GiB、真实后端 Playwright、watch、证书 serial/not_after。

## 验证

- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
