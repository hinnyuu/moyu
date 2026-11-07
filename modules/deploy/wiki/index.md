# deploy 模块（人类说明）

deploy 负责把 moyu 装进一个 Podman pod：一个镜像，按角色启动 gateway、api、worker。

## 构建镜像

在仓库根目录：

```bash
podman build -f modules/deploy/container/Containerfile -t <image> .
```

镜像构建会编译 Web、Rust gateway，并安装 Python 依赖。本地沙箱没有 Podman；GitHub Actions 的 `podman` workflow 会在 amd64 runner 上构建并运行 pod smoke。

## 用 Quadlet 启动

1. 把 `modules/deploy/quadlet/*.pod`、`*.container` 放到 `/etc/containers/systemd/`；
2. 准备 `deploy.env`，填写镜像、目录和端口；
3. `systemctl daemon-reload` 后启动 pod 与容器。

```bash
systemctl start moyu-pod.service
systemctl start moyu-api.service moyu-worker.service
# standalone TLS 才需要：
systemctl start moyu-gateway.service
```

## 两种模式

- 外部 Caddy：不启动 gateway，不发布公网端口；
- standalone TLS：启动 gateway，只由它监听公网端口。

## 当前限制

preview 仍在 api 进程内，tusd 尚未独立成容器；视频/EXR 预览未启用。详见 [模块 docs](../docs/index.md)。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/architecture/runtime-topology.md`：目标拓扑。