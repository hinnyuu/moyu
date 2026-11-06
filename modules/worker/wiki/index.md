# worker 模块（人类说明）

worker 是“真正打包的人”。它从任务表里领一个任务，调用 pipeline，然后汇报成功或失败。

## 什么时候会用到

API 创建任务并置为 `queued` 后，worker 的循环调用 `run_once()`。

## 一个最小例子

```python
from moyu_storage import Storage
from moyu_worker import Worker

worker = Worker(Storage("/data").ensure_layout())
worker.recover()

result = worker.run_once()
if result:
    print(result.job_id, result.status)
```

`run_once()` 只处理一个任务；循环、并发和轮询间隔由部署层决定。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/module-interfaces.md`：JobStore 契约。