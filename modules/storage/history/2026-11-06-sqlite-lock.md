---
date: 2026-11-06
module: storage
commit: (included in this commit)
---

# 并发初始化锁重试

## 改动

- connect 设置 busy_timeout，WAL 锁冲突退避重试 30 秒。
- 新增 8 线程并发 ensure_layout 测试。

## 影响

- 修复多容器同时启动时的 database is locked。
