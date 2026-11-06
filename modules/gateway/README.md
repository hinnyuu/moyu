# gateway

Rust TLS 终止、反向代理、证书热重载、IPv4/IPv6 双栈、管理 API 与 token。

- 当前状态：v0.0.1 阶段 2 最小实现（Rust）。
- 依赖：contracts, config
- 接口：GatewayAdmin；HTTP 路由
- 实现：`rust/src/`
- 测试：`cargo test -p moyu-gateway`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。