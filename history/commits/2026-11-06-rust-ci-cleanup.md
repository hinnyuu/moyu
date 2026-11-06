---
date: 2026-11-06
branch: feat/phase1-core-time-rust-ci
commit: (included in this commit)
modules:
  - core-time
  - gateway
  - wasm-client
docs_impact: false
docs_reason: 仅格式化与 lint 修正，行为、接口和文档描述均未变化
wiki_impact: false
wiki_reason: 无可操作流程变化，不需要教程或排错条目
breaking: false
tests: cargo fmt --check; cargo test --workspace; cargo clippy --workspace --all-targets -- -D warnings; cargo check wasm32; cargo check musl; agent-gate --staged
---

# Rust CI 清理

## 背景

`rust` workflow 首次运行在 Format 步骤失败，本地 clippy 也报出 `manual_is_multiple_of` 与
`useless_conversion`。阶段 1 的 Rust 门禁需要先变绿，才能继续实现后续模块。

## 改动

- 对 workspace 执行 `cargo fmt`，补齐文件末尾换行。
- `DosTime` 的偶数秒校验改用 `is_multiple_of`。
- 测试中的 `i64::from(target - n)` 去掉无效转换。
- 修正 `converts_epoch_to_dos` 的日期断言（DOS 日期字为 34，不是 1）。
- 提交 workspace 的 `Cargo.lock`。

## 影响

- 无运行时行为变化。
- 仅影响 Rust 构建与 CI；Python 原型与契约不变。

## 验证

- `cargo fmt --all --check`
- `cargo test --workspace`（5 passed）
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo check -p moyu-wasm-client --target wasm32-unknown-unknown`
- `cargo check -p moyu-gateway --target x86_64-unknown-linux-musl`
- `python3 modules/agent-gate/src/agent_gate.py check --staged`