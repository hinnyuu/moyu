---
date: 2026-11-06
module: worker
commit: (included in this commit)
---

# 容器入口

## 改动

- 新增 `src/moyu_worker/__main__.py`：启动恢复、循环 `run_once()`、SIGTERM/SIGINT 停止、轮询间隔来自 worker 配置。

## 影响

- 容器可用 `moyu worker` 或 `python -m moyu_worker` 启动。
- 单进程串行执行；并发与硬超时仍待实现。