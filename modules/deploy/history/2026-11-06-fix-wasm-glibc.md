---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# WASM 构建改用 cargo wasm-bindgen

## 改动

- wasm 阶段安装 wasm-bindgen-cli 并非预编译 wasm-pack。
- 新增 WASM_BINDGEN_VERSION 构建参数。

## 影响

- 修复 arm64 GLIBC 2.38 依赖；构建时间增加。
