---
date: 2026-11-06
module: gateway
commit: (included in this commit)
---

# 文件监听与证书元数据

## 改动

- notify watcher + x509-parser。
- 状态字段增加 serial/not_after。

## 影响

- watch 实际生效；证书信息更完整。
