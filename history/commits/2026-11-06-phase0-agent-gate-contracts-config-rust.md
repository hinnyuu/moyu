---
date: 2026-11-06
branch: draft/v0.0.1-architecture
commit: (included in this commit)
modules:
  - docs
  - contracts
  - config
  - agent-gate
  - core-time
  - gateway
  - wasm-client
docs_impact: true
wiki_impact: true
breaking: false
tests: agent-gate unit tests; docs link checks; Rust not compiled (cargo missing)
---

# Phase 0：agent-gate、契约、配置 schema 与 Rust 骨架

## 背景

架构冻结后进入阶段 0：先把机器可读契约、配置 schema、文档门禁和 Rust workspace 骨架搭起来，避免业务实现从不可验证的结构开始。

## 改动

- 新增 `agent-gate` CLI、pre-commit hook、单元测试和 GitHub workflow。
- 新增 OpenAPI 草稿和 PackPlan/MetadataReport/Job/GatewayToken JSON Schema。
- 新增全局配置与 gateway/api/worker/preview/storage/uploads JSON Schema。
- 新增 Rust workspace：`moyu-core`、`moyu-gateway`、`moyu-wasm-client` 三个 crate 骨架。
- 更新 docs、模块 docs/history/wiki、wiki 和根 AGENTS 的门禁命令。

## 影响

- 仍是 Phase 0 骨架，没有媒体处理、ZIP、HTTP、TLS 等业务实现。
- 沙箱没有 cargo/rustc，Rust 骨架未编译；实现阶段在 CI/目标机验证。
- `v0.0.1` 标签仍未创建。

## 验证

- `agent-gate` 对既有分支提交通过。
- agent-gate 单元测试。
- Markdown 链接检查。
- JSON/YAML 文件解析检查。

## 后续

- 接入 OpenAPI/JSON Schema 内容校验。
- 实现 core-time、media-metadata、archive-zip、pipeline 的最小闭环。
