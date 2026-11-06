---
date: 2026-11-06
module: media-metadata
commit: (included in this commit)
---

# 修复测试素材探测

## 改动

- 新增 `available(path)`，捕获不可访问路径的 `OSError`。
- `image_files()` 与视频素材 `skipUnless` 改用 `available`。

## 影响

- CI 上素材不可访问时正常跳过，不再导致测试模块导入失败。
- 本地有素材时仍执行完整矩阵。