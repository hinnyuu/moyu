# 运行时拓扑（v0.0.1）

## 1. 镜像

- 唯一镜像：`ghcr.io/hinnyuu/moyu:<version>`。
- 不使用多镜像微服务；`gateway` 也来自同一个镜像。
- 镜像内包含 Python 运行时、Rust gateway、tusd、ffmpeg、libvips、OpenImageIO、Web 静态文件。
- 通过入口 `moyu <role>` 选择角色。

## 2. 容器

| 容器 | entrypoint | 数据卷 | 网络 | 资源建议 |
| --- | --- | --- | --- | --- |
| `gateway` | `moyu gateway` | 证书目录（只读）、secret 目录 | 监听公网/配置端口；管理 API 仅 Pod 内 | 低 CPU、低内存、只读根文件系统 |
| `api` | `moyu api` | `/data`、`/config`（读写运行配置） | Pod 内 | 0.5–1 CPU、512MB 起 |
| `worker` | `moyu worker` | `/data`、`/config`（只读） | 无公网 | 1 CPU、1–2GB |
| `preview` | `moyu preview` | `/data`、预览缓存 | 无公网 | 1–2 CPU、2–4GB |
| `tusd` | `moyu tusd` | `/data/uploads` | Pod 内 | 低 CPU、低内存 |

- `api` 同时提供 Web 静态文件；不单独设 `web` 容器。
- `worker` 与 `api` 从第一天分开，避免长任务影响接口响应。
- `preview` 独立容器，便于单独限制 CPU/内存和隔离 ffmpeg。
- `tusd` 独立容器；镜像内包含 tusd 二进制。

## 3. 两种部署模式

### 3.1 外部 Caddy 模式

```text
Pod: moyu
├─ api
├─ worker
├─ preview
└─ tusd
```

- `gateway` 不启动。
- 现有 Caddy 负责公网端口、TLS、证书和外部网络。
- Caddy 反向代理到 Pod 内的 api/tusd；具体连通方式由部署环境决定。
- WebUI 不显示证书热重载/网关 token 管理，或显示“外部代理模式”。

### 3.2 Standalone TLS 模式

```text
Pod: moyu
├─ gateway
├─ api
├─ worker
├─ preview
└─ tusd
```

- 只有 `gateway` 监听公网端口。
- 证书目录挂载到 gateway。
- 证书热重载触发方式可配置：默认轮询 + API；watch/SIGHUP 可选。
- gateway 管理 API 监听 Pod 内的回环地址（默认 `127.0.0.1:<admin-port>`）。
- api/worker/preview/tusd 不直接暴露公网。

## 4. Podman pod 与端口

- 推荐使用 Podman 原生 pod + Quadlet，不依赖 Docker Compose。
- 端口不是固定值：由配置/部署文件决定。
- host network 模式：gateway 直接绑定配置端口，不依赖 Podman publish。
- bridge 模式：必须配合 `PublishPort`；改公网端口需要改部署文件并重建 pod/container。
- IPv4/IPv6 双栈：gateway 监听 IPv4 和 IPv6；外部 Caddy 模式由 Caddy 负责。
- 端口变更的生效方式必须写入 wiki 和 WebUI 提示。

## 5. 卷

建议卷布局：

```text
/data/
├─ uploads/
├─ assets/
├─ jobs/
├─ outputs/
├─ preview/
├─ db/
└─ secrets/
/config/
├─ moyu.yaml
├─ modules/*.yaml
├─ secrets/
└─ state/
    ├─ last-known-good/
    └─ backups/
```

- `/data`：业务数据，持久化。
- `/config`：运行配置，持久化；WebUI 可编辑运行配置。
- `/config/secrets` 或 `/run/secrets`：token 等秘密，权限收紧。
- 证书目录独立挂载给 gateway，只读。

## 6. 安全边界

- 单镜像不拆镜像，因此 gateway 容器内也会存在 Python/ffmpeg 等文件；运行时必须加固：
  - 只读根文件系统；
  - 非 root；
  - `cap_drop: ALL`；
  - `no-new-privileges`；
  - 独立 cgroup；
  - gateway 不挂载数据卷，只挂证书；
  - gateway 只运行 gateway 进程。
- api/worker/preview/tusd 不直接发布公网端口。
- preview 处理不可信媒体，必须限制 CPU、内存、PID、超时和并发。
- WebUI 不直接控制 Podman socket；部署拓扑由 Quadlet/pod YAML 管理。

## 7. 资源与轻量服务器

- 所有容器支持独立 CPU/内存/PID 限制。
- preview 最重，可在低配 profile 中降低并发或关闭自动预览。
- 单镜像体积会较大；v0.0.1 接受这个取舍。
- 如果需要降低镜像/拉取体积，才考虑未来拆分 preview/gateway 镜像，但不是当前决策。

## 8. 构建与发布

- 镜像：`ghcr.io/hinnyuu/moyu:<version>`。
- 目标架构：`linux/amd64`；根据 NAS 需要再决定 `linux/arm64`。
- GitHub Workflow：测试 → 构建 → SBOM/漏洞扫描 → 推送 GHCR。
- `v0.0.1` 标签只在架构冻结、实现和端到端验收完成后创建。