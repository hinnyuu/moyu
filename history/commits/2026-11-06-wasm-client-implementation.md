---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - wasm-client
docs_impact: true
wiki_impact: true
breaking: false
tests: cargo test --workspace; cargo clippy --workspace --all-targets -- -D warnings; cargo check -p moyu-wasm-client --target wasm32-unknown-unknown; agent-gate --staged
---

# wasm-client 阶段 2 最小实现

## 背景

浏览器可选 ZIP 是 v0.0.1 的非默认路径，需要先有可验证的 Rust 核心与 WASM 绑定，而不是继续保留占位。

## 改动

- 新增 `modules/wasm-client/rust/src/zip.rs`：STORE ZIP 写入、UTF-8 名称、DOS mtime、无 extra field、CRC32。
- `lib.rs`：`ClientFile`、`pack`、`PackError`，复用 `moyu-core` 的 `plan_times`。
- WASM 绑定：`PackBuilder`（new/add_file/finish）与 `capabilities()`，仅 `wasm32` 编译。
- 限制：512MiB 默认输入、65535 条目、单条 4GiB、仅 STORE。
- 新增 6 个 Rust 单元测试；更新 wasm-client 的 docs/wiki/module.yaml。
- `Cargo.lock` 增加 `wasm-bindgen` 依赖。

## 影响

- 客户端 ZIP 只保证 DOS mtime，不承诺内部媒体元数据。
- 尚未生成可直接加载的 `.wasm`/JS glue，也未接入 Web UI。
- 转码未实现，调用方回退服务端。

## 验证

- `cargo test --workspace`：gateway 5、core 5、wasm-client 6 全部通过。
- `cargo clippy --workspace --all-targets -- -D warnings`：通过。
- `cargo check -p moyu-wasm-client --target wasm32-unknown-unknown`：通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。