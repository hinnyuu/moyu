# media-metadata

识别媒体格式，探测内部时间字段，生成等长补丁或 materialize 重建计划，并在写 ZIP 时流式应用。

- 当前状态：v0.0.1 阶段 1 最小实现（Python）。
- 依赖：contracts, core-time
- 接口：MetadataAdapter：detect / inspect / plan / apply
- 实现：`src/moyu_media_metadata/`
- 测试：`tests/test_media_metadata.py`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。