---
date: 2026-11-06
module: pipeline
commit: (included in this commit)
---

# pipeline 阶段 1 最小闭环

## 改动

- 新增 `src/moyu_pipeline/`，实现 `PackInput` 与 `pack`。
- 串联 `moyu_core_time.plan_times`、`moyu_media_metadata.build_metadata_patches` / `materialize_metadata`、`moyu_archive_zip.ArchiveWriter`。
- 写 manifest：归档 sha256、目标 epoch、delta、每条目 DOS 与元数据字段。
- 失败清理 `.part` 与 materialize 临时文件。
- 新增 7 个集成测试。

## 影响

- 源文件只读；写入后复查大小与 mtime。
- 严格模式遇到未知格式或冲突字段直接失败。
- 未引入 HTTP、数据库或任务状态。