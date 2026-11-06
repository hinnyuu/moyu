# gateway 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

Rust TLS 终止、反向代理、证书热重载、IPv4/IPv6 双栈、管理 API 与 token。

同一镜像的 gateway 容器；rustls + hyper/axum；证书目录挂载；默认轮询 30s + API；watch/SIGHUP 可选；token 共享 secret；管理 API 只回环；流式上传/SSE；standalone 模式启用，external Caddy 模式省略。

## 非职责

不做 ACME、不管理业务数据、不解析媒体。

## 依赖

contracts, config

## 接口

GatewayAdmin；HTTP 路由

## 失败模式

证书无效、私钥不匹配、端口占用、IPv6 不可用、token 失效、反代缓冲。

## 测试

TLS A→B 热重载、双栈、流式、SSE、token、坏证书回退、启动失败。

## 替换点

Rust 实现可替换；接口与证书/管理契约不变。

## Rust 骨架

- workspace member：`modules/gateway/rust`，package `moyu-gateway`。
- 当前只有骨架 `main`，没有 TLS/反代/证书逻辑。
- 沙箱没有 cargo/rustc，未编译；实现阶段验证 musl 构建、证书热重载、双栈、流式转发。
- gateway 与 wasm-client 不互相依赖。
