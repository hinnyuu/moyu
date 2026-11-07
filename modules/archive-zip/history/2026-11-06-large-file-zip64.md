---
date: 2026-11-06
module: archive-zip
commit: (included in this commit)
---

# >4GiB ZIP64 验证

## 改动

- 新增 4GiB+1KiB 稀疏文件 STORE/ZIP64 验证脚本。
- CI 接入。

## 影响

- 覆盖单条目 >4GiB；输出约 4GiB 临时文件。
