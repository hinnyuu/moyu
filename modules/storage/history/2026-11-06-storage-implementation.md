---
date: 2026-11-06
module: storage
commit: (included in this commit)
---

# storage 阶段 2 最小实现

## 改动

- 新增本地 FS + SQLite 实现：`Storage`、`AssetStore`、`JobStore`。
- UUID 生成 ID，拒绝越出数据根的路径。
- 资产登记计算 sha256，配额不足时不移动源文件。
- 任务状态机覆盖 created/queued/running/verifying/succeeded/failed/canceled。
- 上传与预览 TTL 清理。

## 影响

- 任务与资产在重启后仍可读取。
- 尚未实现 S3/NAS 适配器、并发队列与配额预留。