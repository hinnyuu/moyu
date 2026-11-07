# 操作：配置与 WebUI

## 1. 配置目录

```text
/config/
├─ moyu.yaml
├─ modules/
│  ├─ gateway.yaml
│  ├─ api.yaml
│  ├─ worker.yaml
│  ├─ preview.yaml
│  ├─ storage.yaml
│  └─ uploads.yaml
├─ secrets/
└─ state/
   ├─ last-known-good/
   ├─ backups/
   └─ audit.db
```

- 一个模块一个文件；根文件只放全局项。
- Secret 不进普通 YAML；放 `secrets/` 或 `/run/secrets`。
- `/config` 必须持久挂载。

## 2. WebUI 能改什么

| 类型 | WebUI | 生效方式 |
| --- | --- | --- |
| 运行配置 | 可编辑 | 热生效或重启对应容器 |
| 部署配置 | 只读/生成片段 | 重建 pod/container |
| Secret | 生成/轮换/复制一次 | 写 secret 文件，立即/重启 |
| Bootstrap | 首次向导 | 启动时 |

WebUI **不直接控制 Podman socket**。镜像 tag、卷、网络、host 端口映射等由 Quadlet/pod YAML 管理。

## 3. 端口

- 端口在 `gateway.yaml` 的 `listen.port`。
- host network：改配置并重启 gateway。
- bridge：还要改 `PublishPort` 并重建 pod。
- external Caddy：公网端口由 Caddy 管理。
- UI 保存时必须显示生效方式和影响。

## 4. 缺失与损坏

- `/config` 缺失：自动创建默认文件。
- 模块文件缺失：使用默认值并写回。
- 配置非法：优先 `state/last-known-good/`；没有则启动失败或只读恢复。
- schema 升级：启动迁移，迁移前备份。
- 写入：临时文件 + fsync + 原子 rename；单写者；revision/ETag 防并发。

## 5. 格式

- YAML 1.2；
- 严格 schema，拒绝未知字段；
- 禁止 anchor/merge；
- 类型显式；
- 每模块自己的 `schemaVersion`。

## 6. 首次启动

1. 创建 `/config` 默认文件。
2. 生成一次性管理员 bootstrap token，写入受限文件/日志。
3. WebUI 首次向导要求输入 bootstrap token。
4. 设置管理员密码，token 失效。
5. 管理 secret/token 按需生成。

## 7. 变更审计

- 运行时配置修改记录在 `state/audit.db`，不进项目 `history/`。
- 项目 `history/` 只记录代码/契约/schema 变化。
- 当前 API 提供 `GET /api/v1/config/audit`；下载配置、恢复 last-known-good、diff 视图尚未接入 WebUI。