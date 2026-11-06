# pipeline 模块文档

状态：v0.0.1 阶段 1 最小实现（Python）。

## 职责

打包业务编排：扫描/资产输入、时间计划、媒体补丁、ZIP 写入、manifest、校验。

串联 core-time、media-metadata、archive-zip；不依赖 Web、数据库或 HTTP。输入是文件/资产列表和目标时间；输出 ZIP、manifest 与校验结果。

## 非职责

不提供 HTTP、不管理用户、不调度浏览器、不直接持久化任务状态、不修改源文件。

## 依赖

contracts, core-time（`moyu_core_time`）、media-metadata（`moyu_media_metadata`）、archive-zip（`moyu_archive_zip`）。

## 接口

Python 包位于 `src/moyu_pipeline/`：

```python
PackInput(source, arcname)
pack(
    inputs,
    target_epoch,
    output,
    timezone="UTC",
    utc_offset_seconds=None,
    compression="store",
    strict_metadata=False,
    force=False,
    verify=True,
    manifest_path=None,
    chunk_size=1024 * 1024,
) -> {"summary", "manifest", "verify"}
```

流程：

1. `stat` 每个输入，构造 `SourceTime(arcname, mtime_ns)`；
2. `moyu_core_time.plan_times` 计算统一 delta、目标 epoch 和 DOS 时间；
3. 每个条目调用 `moyu_media_metadata.build_metadata_patches`；
4. 等长补丁流式写入；需要 materialize 时先生成临时文件再写入；
5. `moyu_archive_zip.ArchiveWriter` 写 `.part`、校验、原子改名；
6. 复查源文件大小与 mtime 未变化；
7. 写 manifest（含归档 sha256）并再次校验归档。

manifest 条目包含 `arcname`、`source`、`source_mtime_ns`、`target_epoch`、`dos`、`metadata`（format、mode、patches、fields、notes、strict_problems）。

## 配置

- `timezone`：IANA 名称；`UTC` 可直接使用。
- `utc_offset_seconds`：显式覆盖时区偏移；不传时按 `target_epoch` 解析。
- `compression`：`store` 或 `deflate`。
- `strict_metadata`：遇到 `strict_problems` 立即失败。
- `force`：允许覆盖已有输出。

## 失败模式

源文件缺失或变化、目标时间不晚于最新 mtime、重复 arcname、元数据解析/重建失败、严格模式拒绝、归档校验失败、manifest 写入失败、磁盘不足。

失败时删除 `.part` 与 materialize 临时文件，目标归档不出现半成品；已提交到 main 的代码不会修改源文件。

## 测试

`tests/test_pipeline.py` 覆盖：

- 多个纯字节文件的相对时间、DOS 时间、STORE、无 extra、源文件不变；
- PNG `tEXt` 改写、归档内字节包含目标日期；
- PNG 压缩 `zTXt` materialize、临时文件清理、输出可解码；
- 严格模式拒绝未知格式；
- 目标时间过早、重复 arcname、源文件缺失；
- `Asia/Shanghai` 偏移下的 DOS 小时/分钟。

运行：

```bash
PYTHONPATH=modules/pipeline/src:modules/core-time/python:modules/media-metadata/src:modules/archive-zip/src \
  python3 -m unittest discover -s modules/pipeline/tests -v
```

## 替换点

编排逻辑与 adapter/writer 解耦；pipeline 只依赖三者公开接口。替换实现时只改装配与导入路径，不改流程语义。