# 网关管理 API（v0.0.1）

## 1. 范围

gateway 是 standalone HTTPS 模式的 TLS 终止与反向代理。它提供一组**内部管理 API**，用于证书重载和状态查看。

- 只重读挂载证书文件，**不接受上传证书**。
- 默认不暴露公网。
- 外部 Caddy 模式下不启用 gateway，也不启用本 API。

## 2. 内部管理 API

```text
POST /admin/cert/reload
GET  /admin/cert/status
```

鉴权：

```http
Authorization: Bearer <token>
```

### `POST /admin/cert/reload`

- 无请求体；
- 重新读取配置中的 `certFile` / `keyFile`；
- 校验证书链、私钥匹配、有效期；
- 成功原子切换；失败保留旧证书；
- 返回：

```json
{
  "status": "reloaded",
  "cert_loaded_at": "…",
  "cert_sha256": "…"
}
```

`cert_sha256` 是证书文件内容的 SHA-256，不是 X.509 指纹；serial/not_after 尚未解析。

- 失败返回 4xx/5xx 和稳定错误码；
- 不返回私钥内容。

### `GET /admin/cert/status`

- 返回 `status`、`cert_loaded_at`、`cert_sha256`、`reloads`；
- 不返回私钥；
- 可用于 WebUI 和监控。

## 3. 暴露面

默认：

```yaml
api:
  listen: "127.0.0.1:<admin-port>"
```

- 与 api 容器在同一个 Podman pod 内，共享网络 namespace；
- WebUI 通过应用 API 调用网关管理 API，不把 token 交给浏览器；
- 远程 curl 通过 SSH 隧道或 VPN：

```bash
ssh -L <admin-port>:127.0.0.1:<admin-port> user@host
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:<admin-port>/admin/cert/reload
```

- 不建议把管理 API 暴露在公网主端口路径上。

## 4. Token

- 32 字节随机 token，base64url；
- 明文写入共享 secret 文件：
  ```text
  /config/secrets/gateway_reload_token
  ```
- 权限 0600；gateway 每次请求读取文件；轮换后立即生效，无需重启；
- WebUI/API 生成/轮换/撤销，明文只在轮换响应中展示一次；
- 撤销 = 写入空文件或禁用 API；
- 当前不维护 token 数据库元数据、最近使用与审计表，待补。

## 5. 证书重载触发

默认：

- 启动时加载；失败直接退出；
- 每 30 秒轮询；
- API 立即触发。

可选：

- fsnotify 监听；
- SIGHUP。

三者不是同时强制开启，配置决定。

证书目录：

```text
/certs/
├─ tls.crt     # leaf → intermediate 链
└─ tls.key
```

- 挂载目录而不是单文件，避免原子替换在部分运行时下不可见；
- 读取时可容忍写入中的临时状态；
- 新证书无效时保留旧证书。

## 6. WebUI 应用 API

浏览器不直接调用 gateway 管理 API，而是：

```text
POST   /api/v1/admin/gateway/token/rotate
GET    /api/v1/admin/gateway/token
DELETE /api/v1/admin/gateway/token
POST   /api/v1/admin/gateway/cert/reload
GET    /api/v1/admin/gateway/cert/status
```

- 已实现；gateway 未启用时返回 `409 gateway_disabled`；
- 浏览器使用应用会话和 CSRF 防护；
- API 读取 secret 文件并调用 gateway；
- 只有“复制 token”场景才把明文 token 展示给用户一次；
- 外部 Caddy 模式下这些接口返回未启用或隐藏 UI。

## 7. 测试要求

已覆盖：

- 无 token / 错 token / 正确 token（gateway `authorized`）；
- 证书 A → B 热重载与 `cert_sha256` 变化；
- 启动无证书失败；
- IPv4/IPv6 分别握手（人工 E2E）；
- API token 轮换/撤销与文件权限（`test_gateway_admin.py`）；
- API 网关管理代理与 CSRF（`test_api.py`）。

待补：

- 坏证书/私钥不匹配时旧证书继续服务（代码保留旧证书，但缺自动化测试）；
- 大上传和 SSE 经网关不缓冲的自动化测试。