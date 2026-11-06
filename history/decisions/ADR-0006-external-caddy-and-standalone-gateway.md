# ADR-0006：外部 Caddy 与项目自带 TLS 网关并存

- 状态：已接受（v0.0.1 架构草稿）
- 日期：2026-11-06

## 背景

项目需要公网 HTTPS、IPv4/IPv6 双栈和非标准端口，但实际业务环境已有配置好的 Caddy。项目自身也必须在没有 Caddy 时支持挂载证书的 HTTPS。

## 决策

- Caddy 不属于项目组件，不提交 Caddy 配置作为必需文件。
- 支持两种模式：
  1. **external-proxy**：外部 Caddy 负责 TLS/公网端口，项目不启动 gateway。
  2. **standalone-tls**：项目启动 gateway，加载挂载证书，支持热重载和双栈。
- 不使用 ACME；证书由外部系统/挂载文件提供。
- 证书目录：
  ```text
  /certs/tls.crt
  /certs/tls.key
  ```
- 热重载触发可配置：
  - 默认每 30 秒轮询；
  - 管理 API 立即触发；
  - watch/SIGHUP 可选。
- 证书更新 API 只重新读取挂载文件，不接受 HTTP 上传证书/私钥。
- 端口来自配置，不写死；host/bridge 均可，端口变更按模式重启或重建。
- token 由 WebUI 生成/轮换/复制一次，写入共享 secret 文件；gateway 每次请求读取。

## 理由

- 复用现有 Caddy，避免重复 ACME/证书运维。
- 没有 Caddy 时仍能独立部署。
- 挂载证书 + 热重载比项目内置 ACME 更简单、可控。
- 端口配置化避免环境耦合。
- token 管理可由 WebUI 统一操作，远程 curl 仍可用。

## 代价

- 需要维护两种部署 profile。
- gateway 模块必须处理证书热重载、双栈、流式反代。
- bridge 模式改端口需要同步部署文件。
- 外部 Caddy 与 standalone 不能同时占用同一公网端口。

## 验证

- 证书 A→B 热重载无重启。
- IPv4/IPv6 分别握手。
- 无效证书保留旧证书。
- token 轮换立即生效。
- 外部 Caddy 模式不启动 gateway。
- 端口变更按模式在 wiki 中有明确步骤。