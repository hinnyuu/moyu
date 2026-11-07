# 升级与回滚

本文只讲运维操作；镜像里包含什么、容器如何编排见 [Podman 单 Pod 多容器](podman-single-pod.md)。

## 升级前

1. 确认目标标签的 CI 全绿（`agent-gate`、`python`、`rust`、`web`、`podman`）。
2. 备份 `/config`（含 `state/last-known-good` 与 `state/audit.db`）和 `/data`。
3. 记录当前镜像标签，建议用 `sha-<12位>`，不要只用 `latest`。
4. 配置迁移不可逆：先在可写 API 容器完成迁移，再启动只读 worker。

## 升级

```bash
podman pull ghcr.io/<owner>/moyu:<tag>
# 更新 deploy.env 里的 MOYU_IMAGE
systemctl daemon-reload
systemctl restart moyu-api.service moyu-worker.service
systemctl restart moyu-preview.service moyu-tusd.service moyu-gateway.service
```

验证：

```bash
curl -k https://<host>/api/v1/health
```

再登录 WebUI，确认配置 revision、任务与预览正常。

## 回滚

1. 把 `MOYU_IMAGE` 改回上一个标签（推荐 `sha-<12位>`）。
2. 如果新版本改过配置或数据格式，恢复升级前的 `/config` 与 `/data` 备份。
3. `systemctl daemon-reload`，按 api/worker/preview/tusd/gateway 顺序重启。
4. 再次检查健康接口与任务列表。

## 注意

- 配置迁移前会备份到 `config/state/backups/`，但旧版本不一定能读取新 schema；回滚必须恢复配置备份。
- 审计库 `config/state/audit.db` 随配置备份一起保留。
- `latest` 只用于方便，不用于可回滚的生产部署。
