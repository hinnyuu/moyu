# 概念：镜像、容器与 Podman pod

很多人以为“一个镜像只能跑一个容器”，其实不是。

## 1. 镜像和容器

- **镜像（image）**：只读模板，包含文件系统层和启动入口。
- **容器（container）**：镜像的一次运行实例，有自己的进程、可写层、cgroup、日志和重启策略。

同一个镜像可以启动多个容器，只要给不同参数/入口：

```text
ghcr.io/hinnyuu/moyu:<version> api
ghcr.io/hinnyuu/moyu:<version> worker
ghcr.io/hinnyuu/moyu:<version> preview
```

这些容器共享只读镜像层，但进程和资源限制独立。

## 2. Podman pod

Pod 是一组共享网络 namespace 的容器：

- 容器之间可以用 `127.0.0.1` 通信；
- 只有需要公网的容器发布端口；
- 每个容器仍有独立 cgroup、日志、重启策略；
- Podman 原生支持，不需要 Docker Compose。

```text
Pod: moyu
├─ gateway
├─ api
├─ worker
├─ preview
└─ tusd
```

## 3. 为什么不是单容器全塞

单容器里用 supervisor 跑所有进程也能工作，但：

- preview 崩溃/OOM 可能拖垮 api；
- 无法按角色限制 CPU/内存；
- 公网网关和不可信媒体处理共享安全边界；
- 升级一个组件要重启全部。

所以项目选择**单镜像、多容器**。

## 4. 为什么不用 Docker Compose

Podman 原生有：

- `podman pod create` + `podman run --pod`；
- Quadlet（systemd 单元）；
- `podman play kube`（Kubernetes Pod YAML）。

Compose 可以作为开发便利，但不是部署依赖。

## 5. 常见误解

- “一个镜像只能一个容器”：错。
- “一个 pod 只能一个容器”：错，pod 就是多容器组合。
- “多个容器必须多个镜像”：错，镜像和容器是模板和实例的关系。
- “单镜像就必须单容器”：错，单镜像可以跑多容器。