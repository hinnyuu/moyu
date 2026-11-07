# gateway 模块文档

状态：v0.0.1 阶段 2 最小实现（Rust，rustls + hyper）。

## 职责

Rust TLS 终止、反向代理、证书热重载、IPv4/IPv6 双栈、管理 API 与 token。

同一镜像的 gateway 容器；证书目录挂载；默认轮询 30s + 管理 API；SIGHUP 可选；token 共享 secret；管理 API 建议只回环；流式转发；standalone 模式启用，external Caddy 模式省略。

## 非职责

不做 ACME、不管理业务数据、不解析媒体、不做请求体限流。

## 依赖

contracts, config

## 接口

Rust 包位于 `rust/src/`：

- `GatewayConfig`：`listen`、`cert`、`reload`、`upstream`。
- `CertStore`：加载/重载证书，`ArcSwap` 原子替换。
- `proxy::serve`：TLS 接受 + 反向代理。
- `admin::serve`：管理 HTTP API。

管理 API：

- `GET /admin/cert/status`（兼容 `/status`）：`{status,cert_loaded_at,cert_sha256,cert_serial,cert_not_after,reloads}`；
- `POST /admin/cert/reload`（兼容 `/reload`）：重读证书，返回新的 `cert_loaded_at`、`cert_sha256`、`cert_serial`、`cert_not_after`；
- `GET /healthz`：健康检查；
- 所有请求要求 `Authorization: Bearer <token>`；token 来自 `reload.api.tokenFile`，每次请求读取，支持轮换；
- `cert_sha256` 是证书文件的 SHA-256；`cert_serial`/`cert_not_after` 来自 X.509 叶子证书解析。

## 启动

```bash
MOYU_GATEWAY_CONFIG=/config/modules/gateway.yaml moyu-gateway
```

`enabled: false` 时打印 `disabled` 并退出，不监听端口。

## 代理行为

- 下游 TLS 支持 ALPN `h2` 与 `http/1.1`；
- 上游固定 HTTP/1.1，保留路径与查询串；
- 流式转发请求/响应体，不整包缓冲；
- 去除 hop-by-hop 头并重写 `Host`；
- 上游失败返回 `502` 文本错误，不泄露内部路径。

## 证书热重载

- 启动时加载证书/私钥；无效则启动失败。
- `reload.pollInterval` 支持 `ms/s/m/h`，`0s` 关闭轮询。
- `reload.api` 提供立即重载。
- `reload.signal` 为 true 时监听 SIGHUP。
- `reload.watch` 为 true 时监听证书/私钥所在目录，文件变化后重载。

## 配置

```yaml
schemaVersion: 1
enabled: true
listen:
  ipv4: "0.0.0.0"
  ipv6: "::"
  port: <port>
cert:
  certFile: /certs/tls.crt
  keyFile: /certs/tls.key
reload:
  onStart: true
  pollInterval: "30s"
  watch: false
  signal: false
  api:
    enabled: true
    listen: "127.0.0.1:<admin-port>"
    tokenFile: /config/secrets/gateway_reload_token
upstream:
  url: "http://api:<internal-port>"
```

## 失败模式

证书缺失/损坏、私钥不匹配、端口占用、IPv6 不可用、token 文件缺失、上游不可达、TLS 握手失败。

## 测试

```bash
cargo test -p moyu-gateway
cargo clippy -p moyu-gateway --all-targets -- -D warnings
```

单元测试覆盖：配置解析与未知字段拒绝、时间间隔解析、证书加载/重载、缺失文件。

运行时验证：

- TLS 代理到本地上游返回 200 和上游内容；
- 管理 API 鉴权、状态、重载；
- 替换证书后 `POST /reload`，TLS 指纹变化且无需重启；
- IPv4 `127.0.0.1` 与 IPv6 `::1` 同时可访问。

## 已知限制

- 未做 HTTP/3、请求大小限制、速率限制；
- 管理 API token 比较是普通字符串比较；
- 上游只支持 HTTP/1.1。

## 替换点

Rust 实现可替换；接口与证书/管理契约不变。