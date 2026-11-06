---
date: 2026-11-06
branch: feat/phase1-core-time-rust-ci
commit: (included in this commit)
modules:
  - docs
  - core-time
docs_impact: true
wiki_impact: true
breaking: false
tests: GitHub Actions rust workflow; local agent-gate
---

# core-time 最小实现与 Rust CI

## 背景

阶段 1 从最小的 `core-time` 开始，先把相对时间计划和 DOS 时间转换做成可测试的 Rust core。

## 改动

- 实现 `moyu-core` 的时间计划、DOS 转换和 5 个单元测试。
- 新增 `.github/workflows/rust.yml`，验证 fmt/check/test/clippy、WASM target 和 x86_64 musl gateway 构建。
- 更新 core-time docs/wiki/history、Rust workspace 文档。

## 影响

- 仍没有媒体元数据、ZIP、HTTP、Web 实现。
- 本地沙箱无 cargo，Rust 编译验证在 GitHub Actions。
- 不创建 v0.0.1 标签。

## 验证

- 本地 agent-gate。
- GitHub Actions `rust` workflow。
