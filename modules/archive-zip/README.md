# archive-zip

写交付 ZIP：DOS mtime、安全条目名、ZIP64、无时间类 extra field、CRC 与原子改名。

- 当前状态：v0.0.1 阶段 1 最小实现（Python）。
- 依赖：contracts
- 接口：ArchiveWriter：add_entry / finalize / verify
- 实现：`src/moyu_archive_zip/`
- 测试：`tests/test_archive_zip.py`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。