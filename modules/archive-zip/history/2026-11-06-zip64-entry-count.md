---
date: 2026-11-06
module: archive-zip
commit: (included in this commit)
---

# ZIP64 条目数测试

## 改动

- 新增 65536 条目写入/校验测试。

## 影响

- 覆盖 ZIP64 EOCD；>4GiB 单条目仍待外部环境验证。
