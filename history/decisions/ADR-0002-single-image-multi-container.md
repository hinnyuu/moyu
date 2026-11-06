# ADR-0002：单镜像、多容器、单 Podman pod

- 状态：已接受（v0.0.1 架构草稿）
- 日期：2026-11-06

## 背景

需要选择镜像/容器数量、是否使用 Docker Compose，以及 gateway 是否单独镜像。

## 决策

- 只发布一个镜像：`ghcr.io/hinnyuu/moyu:<version>`。
- 使用一个 Podman pod，多容器：
  - `gateway`（standalone 模式；external Caddy 模式省略）
  - `api`
  - `worker`
  - `preview`
  - `tusd`
- 不使用 Docker Compose 作为部署依赖；使用 Podman pod + Quadlet 或 `podman play kube`。
- `api` 与 `worker` 从第一天分开，不合并。
- `preview` 独立容器。
- `tusd` 独立容器。
- 不单独设 `web` 容器；Web 静态文件由 `api` 提供。

## 理由

- 单镜像减少构建/发布/版本协调。
- 多容器保留进程、日志、重启、cgroup 隔离。
- 单容器全塞会让 preview OOM/崩溃拖垮 api，且难以按角色限制资源。
- Podman 原生 pod 不需要 Compose；Quadlet 适合 systemd 单机长期运行。

## 代价

- 镜像包含全部依赖，体积较大。
- gateway 容器也会带着 Python/ffmpeg 文件，公网攻击面比 distroless 大。
- 缓解：gateway 容器只读根文件系统、非 root、cap drop、无数据卷、只挂证书、独立资源限制。
- bridge 模式下端口变更需要改 Quadlet 并重建 pod。

## 替代方案

- 单容器 + supervisor：部署最简单，但资源/安全/崩溃隔离差。
- 多镜像微服务 + Compose：过度设计。
- 拆出 distroless gateway：安全更好，但与“单镜像”决策冲突；保留为未来安全审计选项。