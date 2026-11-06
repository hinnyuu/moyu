---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - gateway
  - config
docs_impact: true
wiki_impact: true
breaking: false
tests: cargo test --workspace; cargo clippy --workspace --all-targets -- -D warnings; python3 -m unittest discover -s modules/config/tests -v; TLS proxy/reload/dual-stack 手工验证; agent-gate --staged
---

# gateway 阶段 2 最小实现

## 背景

standalone 部署需要项目自己的 TLS 入口；external Caddy 模式可以不启用。此前 gateway 只有骨架。

## 改动

- 新增 Rust 实现：`config.rs`、`certs.rs`、`proxy.rs`、`admin.rs`、`main.rs`。
- TLS 终止：rustls，ALPN `h2`/`http/1.1`，`ArcSwap` 热替换 `CertifiedKey`。
- 反向代理：下游 h2/h1，上游 HTTP/1.1，流式请求/响应，去除 hop-by-hop 头，502 文本错误。
- 证书热重载：启动加载、轮询、管理 API、SIGHUP；`watch` 未实现并明确日志。
- 管理 API：`GET /status`、`POST /reload`、`GET /healthz`，Bearer token 来自文件并逐请求读取。
- 双栈：IPv4/IPv6 分别 bind，IPv6 设置 `IPV6_V6ONLY`。
- 配置：`gateway.upstream.url` 加入 schema/defaults/docs；默认 `http://api` 为占位。
- 依赖：tokio/hyper/hyper-util/rustls/tokio-rustls/serde/serde_yaml/socket2/arc-swap；dev 依赖 rcgen/tempfile。
- 新增 5 个 Rust 单元测试；更新 gateway 的 README/docs/wiki/module.yaml。

## 影响

- standalone 模式可以终止 TLS 并转发到 API。
- external Caddy 模式设置 `enabled: false` 即可不启动。
- 尚未实现文件系统 watch、HTTP/3、请求大小/速率限制。

## 验证

- `cargo test --workspace`：全部通过（gateway 5 + core 5）。
- `cargo clippy --workspace --all-targets -- -D warnings`：通过。
- 手工 E2E：
  - TLS 代理本地上游返回上游内容；
  - 管理 API 鉴权、状态、重载；
  - 替换证书后 `POST /reload`，TLS 指纹变化且无需重启；
  - IPv4 `127.0.0.1` 与 IPv6 `::1` 同时访问成功。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。