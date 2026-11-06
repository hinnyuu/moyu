---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - worker
  - storage
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/worker/tests -v; python3 -m unittest discover -s modules/storage/tests -v; agent-gate --staged
---

# worker 阶段 2 最小实现

## 背景

pipeline、storage、config 已可用，需要一个执行器把 queued 任务领取、打包、更新进度并处理取消与重启恢复。

## 改动

- 新增 `modules/worker/src/moyu_worker/`：`Worker`、`WorkerResult`、`WorkerError`。
- 实现 `run_once`：claim → 解析 request → `pipeline.pack` → manifest → verifying → succeeded。
- 实现取消检查、失败回写、事件记录和 `recover()`。
- storage 增加 `claim_next()` 与 `recover_stale()`，更新 storage docs/history。
- 新增 6 个 worker 单元测试。
- 更新 worker 的 README、docs、wiki 和 `module.yaml`。

## 影响

- 单任务执行闭环可用；循环、并发与硬超时由后续 runner 提供。
- worker 失败不删除输出目录，成功后才写 manifest；取消时删除本次输出。
- 尚未接入 API 任务创建与上传 token。

## 验证

- `python3 -m unittest discover -s modules/worker/tests -v`：6 passed。
- `python3 -m unittest discover -s modules/storage/tests -v`：7 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。