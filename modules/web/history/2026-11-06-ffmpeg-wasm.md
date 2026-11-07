---
date: 2026-11-06
module: web
commit: (included in this commit)
---

# ffmpeg.wasm 视频转码

## 改动

- 增加 ffmpeg.wasm 依赖、core 复制脚本、视频转码模块与 UI。
- Vitest 回退测试；fullstack 检查跨源隔离。

## 影响

- 视频本地转码需 COOP/COEP；失败回退服务端。
- 构建产物增加约 31MB。
