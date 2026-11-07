# worker 模块文档

状态：v0.0.1 阶段 2 最小实现（Python）。

## 职责

后台打包任务：拉取 job、执行 pipeline、更新进度、取消、恢复。

独立容器；轮询 SQLite/任务队列；执行 pipeline；进度/阶段/错误写回；取消检查；重启恢复；不与 API 合并。

## 非职责

不提供公网 HTTP、不处理上传、不做预览、不解析媒体格式。

## 依赖

pipeline, storage, config

## 接口

Python 包位于 `src/moyu_worker/`：

容器入口：`moyu worker` / `python3 -m moyu_worker`；配置以只读方式加载，启动时 `recover()`，循环 `run_once()`，SIGTERM/SIGINT 停止。

- `Worker(storage)`
  - `run_once() -> WorkerResult | None`
  - `recover() -> int`
- `WorkerResult`：`job_id`、`status`、`result`、`error`、`to_dict()`。
- `WorkerError`：`code` / `message` / `details`。

## 任务 request

```json
{
  "inputs": [{"asset_id": "<asset-id>", "arcname": "frames/0001.exr"}],
  "target_epoch": 1800000000,
  "timezone": "Asia/Shanghai",
  "output_name": "delivery.zip",
  "compression": "store",
  "strict_metadata": false
}
```

- `inputs` 必填，`asset_id` 必须存在；`arcname` 缺省用资产的原始文件名。
- `target_epoch` 必填，必须晚于最新资产 mtime。
- 输出写到 `outputs/<job-id>/<output_name>`，manifest 写到 `jobs/<job-id>/manifest.json`。

## 执行流程

1. `JobStore.claim_next()` 原子领取一个 `queued` 任务并置为 `running`；
2. 解析 request、读取资产路径；
3. 调用 `pipeline.pack`，写 manifest；
4. 检查任务是否被取消；
5. `running → verifying → succeeded`，进度 90 / 100；
6. 失败写 `failed` 与错误信息，并追加事件。

## 取消与恢复

- 取消发生在领取前：`queued → canceled`，不会被领取。
- 取消发生在执行中：任务已是 `canceled`，打包完成后删除输出与 manifest。
- `recover()` 把 `running`/`verifying` 任务重置为 `queued`，错误信息标记 worker 重启；由调用方决定重试。
- 尚未实现执行中的硬超时与单任务强制终止。

## 失败模式

request 非法、资产不存在、目标时间过早、pipeline/元数据/归档失败、磁盘满、取消。

## 测试

`tests/test_worker.py` 覆盖：

- 成功打包、输出与 manifest、事件序列、进度 100；
- 非法 request、资产不存在；
- 取消任务不被领取；
- `recover()` 重置 running；
- 无任务时返回 `None`。

运行：

```bash
python3 -m unittest discover -s modules/worker/tests -v
```

## 替换点

单进程轮询 → 外部队列/多 worker；只要保持 claim、状态机、事件和取消语义。