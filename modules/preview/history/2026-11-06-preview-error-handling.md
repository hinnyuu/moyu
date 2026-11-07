---
date: 2026-11-06
module: preview
commit: (included in this commit)
---

# 图像解码错误映射

## 改动

- Pillow 打开/解码/编码异常统一转为 PreviewError preview_failed。
- 新增损坏图片 415 测试。

## 影响

- 不再向上抛未处理 OSError。
