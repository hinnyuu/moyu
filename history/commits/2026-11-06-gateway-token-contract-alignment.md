---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
  - gateway
  - config
  - deploy
docs_impact: true
wiki_impact: true
breaking: false
tests: cargo test --workspace; cargo clippy --workspace --all-targets -- -D warnings; python3 -m unittest discover -s modules/api/tests -v; python3 -m unittest discover -s modules/config/tests -v; agent-gate --staged
---

# 网关 token 管理与契约对齐

## 背景

发布前审计发现网关管理接口全部 501，契约路径/字段与代码不一致，token 轮换无法从 WebUI/API 完成。

## 改动

- gateway：
  - 管理路径增加 `/admin/cert/reload`、`/admin/cert/status`，保留 `/reload`/`/status`；
  - 状态/重载响应增加 `cert_sha256`（证书文件 SHA-256）；
  - token 比较改为常量时间；
  - 新增 `sha2`、`subtle` 依赖。
- api：
  - 新增 `GatewayAdminClient`：token 文件读写、证书状态/重载代理；
  - `/api/v1/admin/gateway/*` 从 501 改为真实实现；
  - token 明文只在 rotate 响应返回一次，GET 只返回元数据，DELETE 写空文件；
  - 新增 4 个客户端测试，更新 API 测试为 14 个。
- config：gateway token 文件默认改到 `/config/secrets/gateway_reload_token`，API 可写、gateway 只读。
- deploy：smoke 配置/脚本同步 token 路径；文档更新。
- 契约：`gateway-admin-api.md`、`module-interfaces.md` 与实际实现对齐，明确 `cert_sha256` 不是 X.509 指纹、serial/not_after 未解析、token 审计表待补。

## 影响

- WebUI/API 可以轮换/撤销网关 token 并触发证书重载。
- external Caddy 或 gateway 未启用时返回 `409 gateway_disabled`。
- token 文件权限 0600；gateway 每次请求读取。

## 验证

- `cargo test --workspace`：gateway 5、core 5、wasm 6。
- `cargo clippy --workspace --all-targets -- -D warnings`：通过。
- API 18 tests（含 4 个网关客户端）、config 11 tests：通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
