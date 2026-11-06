---
date: 2026-11-06
module: worker
commit: (included in this commit)
---

# worker 阶段 2 最小实现

## 改动

- 新增 `Worker`、`WorkerResult`、`WorkerError`。
- `run_once()` 领取任务、解析 request、调用 `pipeline.pack`、写 manifest、更新状态与事件。
- 取消在领取前和执行后分别处理；失败写 `failed` 与错误信息。
- `recover()` 调用 storage 的 `recover_stale()`。
- 新增 6 个单元测试。

## 影响

- 单任务执行闭环可用；循环、并发、超时由后续 runner 实现。
- 输出写到 `outputs/<job-id>/`，manifest 写到 `jobs/<job-id>/`。
- 取消发生在打包中时，打包完成后删除输出。