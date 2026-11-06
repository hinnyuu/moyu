# worker

后台打包任务：拉取 job、执行 pipeline、更新进度、取消、恢复。

- 当前状态：v0.0.1 阶段 2 最小实现（Python）。
- 依赖：pipeline, storage, config
- 接口：JobStore、PackPlan、ArchiveWriter
- 实现：`src/moyu_worker/`
- 测试：`tests/test_worker.py`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。