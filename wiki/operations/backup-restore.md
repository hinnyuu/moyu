# 操作：备份与恢复

## 1. 需要备份什么

| 数据 | 位置 | 说明 |
| --- | --- | --- |
| 上传/资产/任务/输出 | `/data` | 业务文件 |
| 预览缓存 | `/data/preview` | 可重建，可选备份 |
| SQLite | `/data/state.db` | 资产、任务、事件、上传会话 |
| 运行配置 | `/config` | 运行配置、last-known-good、`state/audit.db` |
| Secret | `/config/secrets` 或 `/run/secrets` | 权限收紧 |
| 证书 | `/certs` | 由外部证书系统管理 |

## 2. 一致性

- SQLite 使用 WAL；备份前执行 checkpoint 或使用 `.backup`。
- 文件与数据库最好在同一停机窗口备份；至少保证任务状态可恢复。
- 大文件用增量/快照；个人单机可用 rsync/快照。

## 3. 恢复顺序

1. 恢复 `/data` 和 `/config`；
2. 恢复 SQLite；
3. 恢复 secret；
4. 重建 pod/container；
5. 校验任务状态、预览缓存、证书。

## 4. 升级前

- 备份 `/data`、`/config`、secret；
- 记录镜像 tag 和配置版本；
- 确认磁盘空间；
- 按容器依赖顺序重建；
- 失败时回滚镜像 tag + 配置备份。

## 5. 安全

- Secret 备份加密；
- 备份文件权限收紧；
- 不要把 `/data` 和 `/config` 暴露到公网；
- 恢复后检查 token/证书是否需要轮换。