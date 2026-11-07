---
date: 2026-11-06
module: wasm-client
commit: (included in this commit)
---

# 图片转码

## 改动

- 引入 image crate；新增 PNG/JPEG 缩放编码。
- WASM 绑定 transcode；capabilities 声明格式。
- 新增 2 个测试（成功/错误）。

## 影响

- 仅图片；视频转码未实现。
