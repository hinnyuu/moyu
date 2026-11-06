# ADR-0001：网关使用 Rust，并与 WASM 共用 workspace

- 状态：已接受（v0.0.1 架构草稿）
- 日期：2026-11-06

## 背景

网关需要 TLS 终止、证书热重载、IPv4/IPv6 双栈、反向代理、流式上传和 SSE。候选实现是 Go 或 Rust。

## 决策

网关使用 Rust，并与浏览器 WASM 共用一个 Cargo workspace：

- `gateway`：native Rust 二进制；
- `wasm-client`：WASM crate；
- `core-time/rust`（package `moyu-core`）：target-neutral 共享逻辑。

不引入 Go。

## 理由

- Rust WASM 是后续确定路线；再引入 Go 会让项目维护 4 套语言/工具链。
- 一个 Rust workspace 可以统一 Cargo.lock、工具链、CI 缓存、依赖审计。
- 轻量服务器上 Rust 静态二进制体积和内存更可控。
- 证书热重载可用 `rustls::ResolvesServerCert` + `ArcSwap`。
- gateway 与 wasm-client 不互相依赖，仍然模块化。

## 代价

- Rust 编译比 Go 慢，agent 迭代成本更高。
- async Rust、stream body、backpressure 需要更多测试。
- 需要严格约束 target-specific 依赖，避免原生依赖进入 WASM。

## 替代方案

- Go 网关：单点更简单、标准库成熟，但增加一套语言工具链。
- Python TLS 代理：热重载和 HTTP/2 支持较弱，不采用。
- 外部 Caddy 作为唯一入口：外部 Caddy 仍支持，但项目自身还需要 standalone 模式，因此保留 Rust 网关。

## 验收

- 证书 A→B 热重载无重启。
- IPv4/IPv6 双栈。
- 流式上传/SSE 不缓冲。
- 管理 API token/重载语义通过 conformance。
- `cargo check -p wasm-client --target wasm32` 不出现原生依赖。