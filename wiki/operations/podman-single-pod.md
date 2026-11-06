# 操作：Podman 单 Pod 多容器

本文是 v0.0.1 的部署草稿。端口、路径、证书都使用占位符；不要把示例端口当成固定值。实现阶段会根据实际配置补全。

## 1. 镜像与角色

唯一镜像：

```text
ghcr.io/hinnyuu/moyu:<version>
```

容器角色：

| 容器 | 入口 | 作用 |
| --- | --- | --- |
| gateway | `moyu gateway` | TLS、反代、证书热重载（standalone 模式） |
| api | `moyu api` | HTTP API、Web 静态文件 |
| worker | `moyu worker` | 打包任务 |
| preview | `moyu preview` | 媒体预览代理 |
| tusd | `moyu tusd` | 大文件断点续传 |

## 2. 两种模式

### 外部 Caddy 模式

```text
Pod: moyu
├─ api
├─ worker
├─ preview
└─ tusd
```

- 不启动 gateway。
- 现有 Caddy 负责公网端口、TLS、证书。
- Caddy 代理到 api/tusd；具体网络按你的 Caddy 部署决定。

### Standalone TLS 模式

```text
Pod: moyu
├─ gateway
├─ api
├─ worker
├─ preview
└─ tusd
```

- gateway 发布公网端口。
- 证书目录挂载给 gateway。
- 默认轮询证书 + 管理 API 重载。

## 3. 卷

```text
moyu-data:/data
moyu-config:/config
moyu-secrets:/run/secrets
/etc/moyu/certs:/certs:ro
```

- `/data`：上传、资产、任务、输出、预览、SQLite。
- `/config`：运行配置、last-known-good、备份。
- `/run/secrets`：gateway reload token 等。
- `/certs`：证书，只读。

rootless Podman 注意 `:U`/`:Z` 和 SELinux；权限在实现阶段细化。

## 4. 直接用 Podman 命令（示例）

```bash
PORT="${MOYU_PUBLIC_PORT:?请先设置 MOYU_PUBLIC_PORT}"

podman pod create --name moyu -p "${PORT}:${PORT}"

podman run -d --pod moyu --name moyu-api \
  -v moyu-data:/data -v moyu-config:/config \
  ghcr.io/hinnyuu/moyu:<version> api

podman run -d --pod moyu --name moyu-worker \
  -v moyu-data:/data -v moyu-config:/config:ro \
  ghcr.io/hinnyuu/moyu:<version> worker

podman run -d --pod moyu --name moyu-preview \
  -v moyu-data:/data \
  ghcr.io/hinnyuu/moyu:<version> preview

podman run -d --pod moyu --name moyu-tusd \
  -v moyu-data:/data \
  ghcr.io/hinnyuu/moyu:<version> tusd

podman run -d --pod moyu --name moyu-gateway \
  -v /etc/moyu/certs:/certs:ro \
  -v moyu-secrets:/run/secrets:ro \
  --read-only --cap-drop=ALL --security-opt=no-new-privileges \
  ghcr.io/hinnyuu/moyu:<version> gateway
```

说明：

- 只有 gateway 需要公网端口；外部 Caddy 模式把 `pod create -p` 换成 Caddy 可达的内部端口。
- gateway 容器不挂 `/data`，不注入数据库/上传路径。
- 证书目录必须挂目录，不要只挂单个文件。
- 端口由配置/部署决定，不是固定值。

## 5. Quadlet 方式（推荐）

```ini
# ~/.config/containers/systemd/moyu.pod
[Pod]
PodName=moyu
PublishPort=${MOYU_PUBLIC_PORT}:${MOYU_PUBLIC_PORT}
```

```ini
# ~/.config/containers/systemd/moyu-api.container
[Container]
Image=ghcr.io/hinnyuu/moyu:<version>
Pod=moyu.pod
Exec=api
Volume=moyu-data:/data
Volume=moyu-config:/config
```

```ini
# ~/.config/containers/systemd/moyu-worker.container
[Container]
Image=ghcr.io/hinnyuu/moyu:<version>
Pod=moyu.pod
Exec=worker
Volume=moyu-data:/data
Volume=moyu-config:/config:ro
```

```ini
# ~/.config/containers/systemd/moyu-preview.container
[Container]
Image=ghcr.io/hinnyuu/moyu:<version>
Pod=moyu.pod
Exec=preview
Volume=moyu-data:/data
```

```ini
# ~/.config/containers/systemd/moyu-tusd.container
[Container]
Image=ghcr.io/hinnyuu/moyu:<version>
Pod=moyu.pod
Exec=tusd
Volume=moyu-data:/data
```

```ini
# ~/.config/containers/systemd/moyu-gateway.container
[Container]
Image=ghcr.io/hinnyuu/moyu:<version>
Pod=moyu.pod
Exec=gateway
Volume=/etc/moyu/certs:/certs:ro
Volume=moyu-secrets:/run/secrets:ro
ReadOnly=true
DropCapability=ALL
NoNewPrivileges=true
```

启动：

```bash
systemctl --user daemon-reload
systemctl --user start moyu-pod
```

查看：

```bash
podman pod ps
podman ps --pod
podman logs moyu-api
podman logs moyu-gateway
```

## 6. 端口

- 端口配置在 `config/modules/gateway.yaml` 的 `listen.port`。
- host network：该端口就是公网端口，不依赖 Podman publish。
- bridge：`PublishPort` 必须与容器端口一致；修改端口要重建 pod/container。
- external Caddy：公网端口由 Caddy 决定。
- IPv4/IPv6 双栈要分别测试：

```bash
curl -4 "https://host:${PORT}/"
curl -6 "https://host:${PORT}/"
```

## 7. 证书与 token

- 证书：`/certs/tls.crt`、`/certs/tls.key`，挂载目录。
- 热重载默认轮询 + API；watch/SIGHUP 按配置开启。
- token 由 WebUI 生成/轮换/复制；写入 `/run/secrets/gateway_reload_token`。
- 远程 curl 通过 SSH 隧道/VPN，不要把管理 API 暴露公网主路径。

详见 [HTTPS、端口与证书](https-ports-certificates.md)。

## 8. 升级

1. 拉取新镜像；
2. 备份 `/data`、`/config`；
3. 按依赖顺序重建容器（gateway 可最后）；
4. 确认 health/日志；
5. 回滚时使用上一镜像 tag 和配置备份。

不要只 `podman pull` 而不重建容器；运行中的容器仍用旧镜像。

## 9. 故障排查

- Pod 起不来：`podman pod ps`、`podman logs`、端口冲突。
- 权限/SELinux：检查卷 `:Z`/`:U`、UID/GID。
- 证书：文件权限、链顺序、私钥匹配、挂载目录。
- token：secret 文件是否存在、权限、轮换后是否立即生效。
- IPv6：监听地址、防火墙、Podman 网络、Caddy。
- 大上传：反代缓冲、请求体限制、tusd 偏移。
- 外部 Caddy：能否到达 Pod 内 api/tusd，Host/X-Forwarded 头。