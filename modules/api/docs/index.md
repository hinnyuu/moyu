# api 模块文档

状态：v0.0.1 阶段 2 最小实现（FastAPI + 会话认证）。

## 职责

HTTP API、认证、任务/上传接口、Web 静态文件、管理接口聚合。

FastAPI + OpenAPI；会话认证/CSRF；任务、上传、预览、下载、配置、网关管理；同源服务 Web 静态；不包含打包/媒体处理实现，只编排。

## 非职责

不执行打包、不生成预览、不直接控制 Podman。生产环境分片由 tusd 处理；同源/开发模式可使用内置 tus 兼容分片端点。

## 依赖

contracts, pipeline, storage, uploads, preview, config

## 认证

`AuthManager` 使用三个外部文件（路径由部署提供，不写死）：

- `bootstrap_token_file`：首次启用的 bootstrap token；
- `state_file`：管理员密码哈希与会话版本；
- `secret_file`：会话签名密钥，缺失时生成 32 字节随机值，权限 0600。

流程：

1. 未配置时，`POST /api/v1/auth/session` 携带 `bootstrap_token` 与新密码完成初始化；
2. 已配置时，携带 `password` 登录；
3. 密码以 PBKDF2-HMAC-SHA256（210000 轮）保存；
4. 会话 cookie 是 HMAC-SHA256 签名的 JSON（`sub/csrf/iat/exp`），HttpOnly、SameSite=Lax；
5. CSRF token 同时写入可读 cookie `moyu_csrf`，写操作要求 `X-CSRF-Token` 与签名会话中的值一致。

单管理员、无找回流程、无速率限制；TLS 模式下应设置 `cookie_secure=True`。

## 接口

容器入口：`moyu api` / `python3 -m moyu_api`；读取 `MOYU_CONFIG_DIR` 与认证文件环境变量，监听 `MOYU_API_LISTEN=host:port`。

`create_app(storage, config_provider, auth) -> FastAPI`，挂载：

- `GET /api/v1/health`
- `POST/GET/DELETE /api/v1/auth/session`
- `GET /api/v1/config`、`GET /api/v1/config/audit`、`GET/PUT /api/v1/config/{module}`
- `POST /api/v1/uploads`、`GET/PATCH /api/v1/uploads/{id}`、`POST /api/v1/uploads/{id}/finish`
- `POST /api/v1/internal/tusd/hook`（内部，token 校验，tusd pre-create/post-finish）
- `POST/GET /api/v1/jobs`、`GET/DELETE /api/v1/jobs/{id}`、`GET /api/v1/jobs/{id}/events`（SSE）、`GET /api/v1/jobs/{id}/download`
- `GET /api/v1/assets/{id}/download`
- `GET /api/v1/previews/{id}/{profile}`（配置 `preview.serviceUrl` 时代理内部预览服务，否则进程内 Pillow）
- `POST /api/v1/admin/gateway/cert/reload`、`GET /api/v1/admin/gateway/cert/status`、`POST /api/v1/admin/gateway/token/rotate`、`GET/DELETE /api/v1/admin/gateway/token`、`GET /api/v1/admin/gateway/token/audit`

网关管理接口通过 `GatewayAdminClient` 调用 gateway 内部管理 API；gateway 未启用时返回 `409 gateway_disabled`。token 轮换写入 `gateway.reload.api.tokenFile`，明文只在轮换响应中返回一次。

`PUT /api/v1/config/{module}` 请求体：`{"patch": {...}, "revision": "<sha256>"}`；revison 不匹配返回 409。

`PATCH /api/v1/uploads/{id}` 需要 `Upload-Offset` 头与 `application/offset+octet-stream` 请求体，返回 204 与新偏移量。

`POST /api/v1/jobs` 请求体即 worker 的 job request；创建后状态为 `queued`。

## 配置

- `api.maxJsonBodyBytes`：JSON 请求体上限；
- `api.session.cookieName` / `ttlSeconds`：cookie 名与 TTL；
- `api.webRoot`：存在时挂载静态 SPA；
- `uploads.*`：上传上限、TTL、chunk size、tus 基础路径；
- `preview.*`：缓存目录、并发、内存、超时、profile。

认证文件路径由装配代码传入，不来自普通 YAML。

## 失败模式

认证失败、CSRF 失败、bootstrap token 错误、密码错误、session 过期、请求体过大、配置 revision 冲突、任务/资产不存在、上传未完成、预览格式不支持、gateway 未启用/不可达。

错误统一为 `{"code","message","details","module"}`。

## 测试

`tests/test_auth.py`（7 个）：密码哈希、初始化、登录、错误 token/密码、签名篡改、过期、CSRF、文件权限。

`tests/test_api.py`（8 个）：健康检查与认证、配置读写与 audit、上传/下载/预览、任务 + worker、取消与 404、网关管理代理与 token、tusd hook、请求体上限。`tests/test_gateway_admin.py`（4 个）：网关管理客户端/token/不可达；`tests/test_preview_client.py`（3 个）：预览服务客户端/错误/不可达。

运行：

```bash
python3 -m unittest discover -s modules/api/tests -v
```

## 替换点

FastAPI → 其他框架，OpenAPI 契约不变；认证可换 OIDC/外部 IdP，但会话/CSRF 语义必须保持。