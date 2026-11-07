# storage 模块文档

状态：v0.0.1 阶段 2 最小实现（Python）。

## 职责

上传暂存、资产、任务、输出、预览缓存、配额和清理。

本地文件系统适配器优先；数据根目录由配置决定；上传暂存、资产、任务工作区、输出、预览缓存分区；配额、TTL、孤儿清理；不直接暴露 HTTP。

## 非职责

不做 HTTP、不生成预览、不解析媒体格式、不管理上传协议。

## 依赖

contracts

## 接口

Python 包位于 `src/moyu_storage/`：

- `Storage(data_root, quota_bytes=0)`
  - `ensure_layout()`、`connect()`、`used_bytes()`、`check_quota(additional=0)`
  - `upload_path` / `asset_path` / `job_dir` / `output_path` / `preview_path`
  - `cleanup(upload_ttl_seconds=None, preview_ttl_seconds=None)`
- `AssetStore(storage)`：`register_asset`、`get_asset`、`path_for`、`open_asset`、`list_assets`、`delete_asset`
- `JobStore(storage)`：`create_job`、`get_job`、`list_jobs`、`claim_next`、`recover_stale`、`update_status`、`cancel_job`、`append_event`、`events`
- `StorageError`：`code` / `message` / `details`

## 目录布局

```text
<dataRoot>/
├─ uploads/<session-id>/data
├─ assets/<asset-id>
├─ jobs/<job-id>/
├─ outputs/<job-id>/<name>
├─ preview/<asset-id>/<profile>/
└─ state.db
```

ID 由模块生成（UUID），路径不接受用户输入；所有路径解析后必须仍在数据根目录内。

## 数据模型

- `Asset`：id、original_name、path、size、sha256、media_type、created_at。
- `Job`：id、status、request(JSON)、progress、error、created_at、updated_at。
- `JobStore` 状态机：

```text
created → queued → running → verifying → succeeded
                  ↘ failed      ↘ failed
created/queued/running → canceled
```

- `job_events` 记录阶段事件，不进入项目 `history/`。

领取与恢复：

- `claim_next()` 用条件更新原子领取最早的 `queued` 任务并置为 `running`；
- `recover_stale()` 把 `running`/`verifying` 任务重置为 `queued`，供 worker 重启后重试。

## 并发初始化

- 所有连接设置 `busy_timeout=30000`；
- 首次启用 WAL 时若遇到 `database is locked`，在 30 秒内退避重试；
- api/worker/preview 同时启动时不会因建表/WAL 切换互相失败。

## 配额与清理

- `quotaBytes <= 0` 表示不限制；否则登记资产前检查已用空间。
- `cleanup` 删除过期上传会话目录与预览 profile；删除空资产目录。
- 清理只处理 `uploads/` 与 `preview/`，不删除已登记资产和任务输出。

## 失败模式

磁盘满、权限不足、路径逃逸、配额超限、任务状态非法、资产不存在、数据库不可用。

## 测试

`tests/test_storage.py` 覆盖：

- 目录布局与路径逃逸拒绝；
- 资产登记/读取/删除与 sha256；
- 配额拒绝时不移动源文件；
- 任务状态机、取消、终态保护、事件；
- 新实例重启后读取同一数据库；
- 上传与预览 TTL 清理；
- 8 线程并发 `ensure_layout`。

运行：

```bash
python3 -m unittest discover -s modules/storage/tests -v
```

## 替换点

本地 FS → NAS/S3；SQLite → 其他元数据存储。替换必须保持 ID 策略、路径安全、配额、TTL 与状态机语义。