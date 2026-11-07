---
date: 2026-11-06
module: wasm-client
commit: (included in this commit)
---

# 改用 wasm-bindgen CLI

## 改动

- 浏览器包通过 cargo + wasm-bindgen CLI 生成，不再依赖 wasm-pack 预编译二进制。

## 影响

- 版本需与 Cargo.lock 的 wasm-bindgen 0.2.130 对齐。
