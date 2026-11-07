---
date: 2026-11-06
module: preview
commit: (included in this commit)
---

# 独立预览服务与视频/EXR

## 改动

- 新增 FastAPI 内部服务与容器入口。
- 新增 ffmpeg 视频 probe/poster/MP4 代理和 oiiotool EXR 预览。
- 新增 3 个服务测试。

## 影响

- 工具不可用时 probe 返回 unsupported，不伪装成功。
- HLS 未实现。
