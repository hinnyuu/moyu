---
date: 2026-11-06
module: preview
commit: (included in this commit)
---

# preview 阶段 2 最小实现

## 改动

- 新增 Pillow 图片 provider：probe、thumb/view/custom profile、缓存、删除。
- 缓存键为资产 sha256 与规范化 profile 的 sha256。
- 内存估算超过上限时拒绝；并发用信号量限制；生成后检查超时。
- 视频/EXR 明确返回不支持。
- 新增 6 个单元测试。

## 影响

- 图片预览闭环可用；视频/EXR 需要后续 provider。
- 缓存位于 storage 的 preview 目录，可由 storage 的 TTL 清理。