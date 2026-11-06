---
date: 2026-11-06
module: archive-zip
commit: (included in this commit)
---

# archive-zip 阶段 1 最小实现

## 改动

- 新增 `src/moyu_archive_zip/`：DOS 编解码、流式写入器、结构校验器。
- `ArchiveWriter` 写 `.part`，可选校验后原子改名；`abort()` 清理临时文件。
- `verify_archive` 拒绝时间类 extra（`0x5455`、`0x000a`、`0x5855`、`0x000d`）、不安全条目名、重复条目、加密与 data descriptor。
- 新增 15 个单元测试，覆盖 STORE/DEFLATE、ZIP64 extra、CRC、期望条目与原子性。

## 影响

- 对外接口稳定为 `ArchiveWriter` / `verify_archive`。
- 不解析媒体格式，不写 manifest，不修改源文件。
- 仍未创建 v0.0.1 标签。