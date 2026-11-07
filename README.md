# moyu

把已经完成、但还没提交的渲染序列“重新出炉”的工具。

## 项目目标

- 以**交付 ZIP**为核心：ZIP 内部记录调整后的 DOS mtime，解压后由新 inode 自然重置 ctime/btime。
- 默认在服务端完成媒体元数据改写和打包；浏览器 WASM 处理作为可选路径。
- 单机、轻量服务器、Podman 原生部署；不把 Docker Compose 作为部署依赖。
- 面向 agent 长期维护：模块、文档、history、wiki 严格分离。
- 公网 HTTPS、IPv4/IPv6 双栈；Caddy 可由外部提供，项目自身也支持挂载证书的 TLS 网关。

## 架构一句话

**一个镜像 + 一个 Podman pod + 多容器**：

- 镜像：`ghcr.io/hinnyuu/moyu`
- 容器：`gateway`（可选）、`api`、`worker`、`preview`、`tusd`
- 外部 Caddy 模式：不启动 `gateway`，由 Caddy 负责 TLS 和公网端口
- Standalone 模式：启动 `gateway`，挂载证书，支持热重载和双栈

## 仓库地图

```text
docs/         当前事实：架构、契约、开发、运维
history/      项目级历史：提交记录、ADR、版本记录
wiki/         人类教程：入门、概念、操作、排错
modules/      模块实现与模块级 docs/history/wiki
```

每个模块目录至少包含：

```text
module.yaml
README.md
AGENTS.md
docs/
history/
wiki/
```

## 开始阅读

- [架构总览](docs/architecture/overview.md)
- [运行时拓扑](docs/architecture/runtime-topology.md)
- [模块清单](docs/architecture/modules.md)
- [配置契约](docs/contracts/config.md)
- [Podman 单 Pod 多容器操作](wiki/operations/podman-single-pod.md)
- [Agent 维护规则](AGENTS.md)

## 当前状态

- `main` 已包含 v0.0.1 阶段实现：core-time、media-metadata、archive-zip、pipeline、config、storage、uploads、preview、worker、api、web、gateway、deploy、wasm-client 核心、agent-gate。
- 已验证：Python 单元测试、Rust 测试/clippy/wasm target、进程级 E2E、amd64 Podman smoke、Web typecheck/build。
- 仍在补齐：preview/tusd 独立容器、视频/EXR 预览、Web 批量/断点/WASM 接入、config 迁移与审计、gateway token 管理、GHCR 发布。
- 尚未创建 `v0.0.1` 标签或 release。

## License

MIT