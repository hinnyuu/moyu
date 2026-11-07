# Rust Workspace（v0.0.1）

## 1. 结论

项目使用**一个 Cargo workspace、三个独立 crate**：

```text
/Cargo.toml
/modules/gateway/rust/        # native binary
/modules/wasm-client/rust/    # cdylib / wasm
/modules/core-time/rust/      # target-neutral library, package: moyu-core
```

不把 gateway 和 wasm 合并成一个 crate，也不引入 Go。

## 2. 职责

| crate | 目标 | 职责 |
| --- | --- | --- |
| `gateway` | `x86_64-unknown-linux-musl` | TLS、反向代理、证书热重载、双栈、管理 API |
| `wasm-client` | `wasm32-unknown-unknown` | 浏览器 ZIP、预览转码的 Rust 部分 |
| `moyu-core` | native + wasm | 时间、DOS 时间、契约类型等 target-neutral 逻辑 |

## 3. 依赖规则

- `gateway` 与 `wasm-client` **不互相依赖**。
- 两者只可依赖 `moyu-core`。
- `moyu-core` 不得引入 `tokio`、文件系统、TLS、网络等原生依赖。
- 原生依赖与 WASM 依赖用 target 区分：

```toml
[target.'cfg(not(target_arch = "wasm32"))'.dependencies]
tokio = { version = "...", features = ["rt-multi-thread", "net", "time", "signal"] }
hyper = "..."
rustls = "..."
tokio-rustls = "..."
arc-swap = "..."
notify = "..."
axum = "..."          # 或直接用 hyper + tower
socket2 = "..."

[target.'cfg(target_arch = "wasm32")'.dependencies]
wasm-bindgen = "..."
js-sys = "..."
web-sys = "..."
```

- workspace `resolver = "2"`。
- 每次检查 WASM 依赖树：
  ```text
  cargo tree -p wasm-client --target wasm32-unknown-unknown
  ```
  不应出现 tokio/rustls/文件系统依赖。

## 4. 常用命令

常用命令：

```text
cargo check -p moyu-gateway
cargo check -p moyu-wasm-client --target wasm32-unknown-unknown
cargo build --release -p moyu-gateway --target x86_64-unknown-linux-musl
cargo build -p moyu-wasm-client --target wasm32-unknown-unknown --release
wasm-bindgen --target web --out-dir modules/web/app/public/wasm \
  target/wasm32-unknown-unknown/release/moyu_wasm_client.wasm
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
```

## 5. CI

- 一个 workspace，一个 `Cargo.lock`。
- CI 分 job：
  - gateway native check/test/build；
  - wasm-client target check + wasm-bindgen CLI；
  - clippy/fmt/test；
  - 共享 cargo 缓存。
- 发布镜像构建 gateway 二进制与 WASM 产物，Web 静态资源一并打包。
- 不使用 Go 工具链。

## 6. 文档边界

- workspace 只是构建/依赖边界，不是文档边界。
- `gateway` 的 docs/history/wiki 在 `modules/gateway/`。
- `wasm-client` 在 `modules/wasm-client/`。
- `moyu-core` 在 `modules/core-time/`。
- 根 `docs/development/rust-workspace.md` 只解释构建规则。

## 7. 什么时候拆 workspace

只有出现以下情况才拆：

- WASM 与 gateway 的依赖/工具链互相拖累；
- 两模块发布节奏完全独立；
- `moyu-core` 无法保持 target-neutral；
- 网关需要独立依赖冻结和安全审计。

当前规模不建议拆。

## Rust CI

`.github/workflows/rust.yml` 在 GitHub Actions 中验证：

- `cargo fmt --all --check`
- `cargo check --workspace`
- `cargo test --workspace`
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo check -p moyu-wasm-client --target wasm32-unknown-unknown`
- `cargo build -p moyu-gateway --release --target x86_64-unknown-linux-musl`

本地沙箱没有 cargo 时，以 CI 结果为准。
