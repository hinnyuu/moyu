---
date: 2026-11-06
module: web
commit: (included in this commit)
---

# 视频转码入口与测试登录

## 改动

- 视频按钮独立于 Rust WASM 区块。
- fullstack 测试统一 login helper。

## 影响

- ffmpeg.wasm 不依赖 wasm-client 产物。
