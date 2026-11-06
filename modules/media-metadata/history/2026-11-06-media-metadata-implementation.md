---
date: 2026-11-06
module: media-metadata
commit: (included in this commit)
---

# media-metadata 阶段 1 最小实现

## 改动

- 新增 `src/moyu_media_metadata/core.py`，覆盖 EXR、PNG、JPEG、TIFF、WebP、AVIF、MP4/MOV、MKV 的探测、补丁计划与 materialize。
- 新增 `adapters.py`：格式注册表、header 识别、`adapter_by_name` / `adapter_for`。
- 新增 8 个模块测试：图片矩阵、MP4 合成容器、PNG 压缩 zTXt、视频素材、未知格式、适配器。
- 测试改为直接调用模块 API，不再调用根目录 `moyu-pack`。

## 影响

- 补丁等长、区间不重叠；压缩字段走 materialize。
- 无法识别的格式返回 `format="unknown"` 并写入 `strict_problems`。
- 源文件不被修改。