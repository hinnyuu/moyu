---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - deploy
  - wasm-client
  - web
docs_impact: true
wiki_impact: false
wiki_reason: 构建工具链变化不影响用户操作
breaking: false
tests: bash -n modules/web/app/scripts/build-wasm.sh; agent-gate --staged
---

# 修复 arm64 WASM 构建的 GLIBC 依赖

## 背景

`podman-arm64` 构建失败：wasm-pack 下载的预编译 wasm-bindgen 需要 `GLIBC_2.38`，而 Debian bookworm 构建镜像只有 2.36。

## 改动

- 镜像 wasm 阶段不再使用 wasm-pack：
  - `cargo install wasm-bindgen-cli --version 0.2.130 --locked`；
  - `cargo build -p moyu-wasm-client --target wasm32-unknown-unknown --release`；
  - `wasm-bindgen --target web` 输出到 `/wasm-out`。
- 新增 `ARG WASM_BINDGEN_VERSION=0.2.130`，与 `Cargo.lock` 对齐。
- 本地 `build-wasm.sh` 同样改为 cargo + wasm-bindgen CLI。
- wasm-client/deploy 文档同步。

## 影响

- 不再依赖预编译二进制，amd64/arm64 均在本机构建，避免 GLIBC 不匹配。
- wasm 构建时间增加（需编译 wasm-bindgen-cli）。
- 升级 wasm-bindgen crate 时必须同步 `WASM_BINDGEN_VERSION`。

## 验证

- 本地无 Rust/arm64 环境，未实际构建。
- 脚本语法检查通过。
- 待 `podman` 与 `podman-arm64` workflow 确认。
