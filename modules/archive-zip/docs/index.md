# archive-zip 模块文档

状态：v0.0.1 阶段 1 最小实现（Python）。

## 职责

写交付 ZIP：DOS mtime、安全条目名、ZIP64、无时间类 extra field、CRC 与原子改名。

默认 STORE，不压缩；条目时间只写 DOS mtime；允许 ZIP64 `0x0001`，拒绝 `0x5455`、`0x000a`、`0x5855`、`0x000d` 等时间字段；写 `.part`，校验通过后原子改名。

## 非职责

不解析媒体格式、不计算时间策略、不负责上传、不写 manifest。

## 依赖

contracts

## 接口

Python 包位于 `src/moyu_archive_zip/`，对外导出：

- `ArchiveWriter(output, compression="store", force=False, fsync=True, verify=True, timezone="UTC", chunk_size=...)`
  - `add_entry(arcname, dos_time, stream, size=None, mode=0o644, force_zip64=False)`
  - `add_file(arcname, dos_time, path, mode=0o644)`
  - `finalize() -> ArchiveSummary`
  - `abort()`
- `verify_archive(path, expected=None, timezone="UTC", strict=True, require_store=False, check_crc=False)`
- `encode_dos` / `decode_dos` / `validate_dos`
- `ArchiveError`

`dos_time` 是 `(year, month, day, hour, minute, second)`，秒必须是 0–58 的偶数。`expected` 是 arcname 到 `{"dos": [...], "target_epoch": ...}` 的映射，用于打包后校验。

## 失败模式

磁盘不足、源文件变化、extra field 泄漏、DOS 时间非法、ZIP64 异常、条目名不安全、重复条目。

失败时 `.part` 文件被删除，目标路径不会出现半成品。

## 大文件验证

`scripts/large_file_e2e.py` 创建 4GiB+1KiB 稀疏文件，STORE 写入 ZIP64，校验 central directory 与条目大小。当前环境结果：PASS，输出约 4.0GiB，耗时约 20 秒。

## 测试

`tests/test_archive_zip.py` 覆盖：DOS 编解码与范围、STORE/DEFLATE、条目名安全、重复条目、字节数不一致、源文件写入、ZIP64 extra、65536 条目 ZIP64 EOCD、原子性、UT/未知 extra 拒绝、期望条目不匹配、CRC 校验。

运行：

```bash
python3 -m unittest discover -s modules/archive-zip/tests -v
```

## 替换点

Python 实现可换 Rust；语义 conformance 不要求 ZIP 字节完全一致，但必须满足同一套校验规则。