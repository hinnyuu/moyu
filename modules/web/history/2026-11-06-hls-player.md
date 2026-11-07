---
date: 2026-11-06
module: web
commit: (included in this commit)
---

# HLS 播放器

## 改动

- 新增 HlsPreview 组件，动态导入 hls.js。
- 上传页选择资产后可播放 HLS。

## 影响

- 首屏不加载 hls.js；非视频资产显示错误提示。
