# 部署模式（v0.0.1）

项目支持两种部署模式，均使用**一个镜像**和**一个 Podman pod**；不使用 Docker Compose 作为依赖。

## 1. 外部 Caddy 模式

适用：已有 Caddy，证书、HTTPS、公网端口由 Caddy 管理。

```text
Pod: moyu
├─ api
├─ worker
├─ preview
└─ tusd
```

- 不启动 `gateway`。
- Caddy 反向代理到 api/tusd；具体网络由部署环境决定。
- WebUI 中证书/网关 token 管理隐藏或标记为“外部代理模式”。
- 公网端口由 Caddy 配置，不由项目配置。

## 2. Standalone TLS 模式

适用：没有 Caddy，项目自己终止 TLS。

```text
Pod: moyu
├─ gateway
├─ api
├─ worker
├─ preview
└─ tusd
```

- 只有 `gateway` 发布公网端口。
- 证书目录挂载到 gateway：
  ```text
  /certs/tls.crt
  /certs/tls.key
  ```
- 默认轮询 30s + API 重载；SIGHUP 可选；watch 未实现，使用轮询/管理 API。
- gateway 管理 API 监听 Pod 内回环地址。
- api/worker/preview/tusd 不直接暴露公网。

## 3. 端口

端口不是固定值：

- gateway 监听端口来自 `config/modules/gateway.yaml` 的 `listen.port`；
- host network 模式：该端口就是公网端口，无需 Podman publish；
- bridge 模式：还需要 Quadlet `PublishPort`，修改端口要重建 pod/container；
- external Caddy 模式：公网端口由 Caddy 决定。

## 4. 卷

```text
/data/     上传、资产、任务、输出、预览、SQLite
/config/   运行配置、secret、last-known-good、备份
/certs/    证书（只读，挂载给 gateway）
```

## 5. 安全

- 单镜像下 gateway 容器也包含 Python/ffmpeg 等文件，运行时必须只读、非 root、cap drop、无数据卷。
- preview 独立容器并限制资源。
- api/worker/preview/tusd 不发布公网端口。
- WebUI 不控制 Podman socket。

## 6. 详细操作

见 [Podman 单 Pod 多容器操作](../../wiki/operations/podman-single-pod.md) 和 [HTTPS、端口与证书](../../wiki/operations/https-ports-certificates.md)。