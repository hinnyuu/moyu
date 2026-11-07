---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# fullstack E2E 日志与超时

## 改动

- api/worker 启动加 PYTHONUNBUFFERED。

## 影响

- 失败时能拿到 worker 日志。
