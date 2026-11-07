---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
  - preview
  - wasm-client
  - web
docs_impact: true
wiki_impact: true
breaking: false
tests: agent-gate --staged
---

# 发布前文档四轮校对

## 背景

前三轮后仍有 HLS/转码已完成却标“待补”、网关状态字段、Secret 存储与测试数量不一致。

## 改动

- architecture/modules/overview：HLS、WASM 转码改为已实现；网关 watch 标注未实现。
- wasm-client README/docs：Rust 图片转码与 Web ffmpeg.wasm 视频转码区分。
- wiki HTTPS：token 存文件而非数据库 hash；状态返回 `cert_sha256`。
- wiki configuration：审计库路径与 WebUI 未接入的下载/恢复/diff。
- deployment-modes/runtime-topology：watch 未实现，SIGHUP 可选。
- API docs 测试数量与覆盖更新。
- preview/web docs 移除过期“待补”。
- 发布清单更新视频转码自动化状态。

## 影响

- 文档只保留真实未完成项：视频转码成功路径未自动化、watch、证书 serial/not_after、截图基线等。

## 验证

- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
