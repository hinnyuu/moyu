# api 模块文档

状态：v0.0.1 阶段 2 最小实现（FastAPI + 会话认证）。

## 职责

HTTP API、认证、任务/上传接口、Web 静态文件、管理接口聚合。

FastAPI + OpenAPI；会话认证/CSRF；任务、上传、预览、下载、配置、网关管理；同源服务 Web 静态；不包含打包/媒体处理实现，只编排。

## 非职责

不执行打包、不生成预览、不直接控制 Podman、不实现 tus 分片传输。

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

`create_app(storage, config_provider, auth) -> FastAPI`，挂载：

- `GET /api/v1/health`
- `POST/GET/DELETE /api/v1/auth/session`
- `GET /api/v1/config`、`GET/PUT /api/v1/config/{module}`
- `POST /api/v1/uploads`、`GET /api/v1/uploads/{id}`、`POST /api/v1/uploads/{id}/finish`
- `POST/GET /api/v1/jobs`、`GET/DELETE /api/v1/jobs/{id}`、`GET /api/v1/jobs/{id}/events`（SSE）
- `GET /api/v1/assets/{id}/download`
- `GET /api/v1/previews/{id}/{profile}`
- `POST /api/v1/admin/gateway/cert/reload`、`GET /api/v1/admin/gateway/cert/status`、`POST /api/v1/admin/gateway/token/rotate`、`GET/DELETE /api/v1/admin/gateway/token`

网关管理接口当前返回 `501 gateway_admin_unavailable`，等待 gateway 客户端接入。

`PUT /api/v1/config/{module}` 请求体：`{"patch": {...}, "revision": "<sha256>"}`；revison 不匹配返回 409。

`POST /api/v1/jobs` 请求体即 worker 的 job request；创建后状态为 `queued`。

## 配置

- `api.maxJsonBodyBytes`：JSON 请求体上限；
- `api.session.cookieName` / `ttlSeconds`：cookie 名与 TTL；
- `api.webRoot`：存在时挂载静态 SPA；
- `uploads.*`：上传上限、TTL、chunk size、tus 基础路径；
- `preview.*`：缓存目录、并发、内存、超时、profile。

认证文件路径由装配代码传入，不来自普通 YAML。

## 失败模式

认证失败、CSRF 失败、bootstrap token 错误、密码错误、session 过期、请求体过大、配置 revision 冲突、任务/资产不存在、上传未完成、预览格式不支持、上游 501。

错误统一为 `{"code","message","details","module"}`。

## 测试

`tests/test_auth.py`（7 个）：密码哈希、初始化、登录、错误 token/密码、签名篡改、过期、CSRF、文件权限。

`tests/test_api.py`（7 个）：健康检查与认证、配置读写与 revision、上传/下载/预览、任务 + worker、取消与 404、网关 501、请求体上限。

运行：

```bash
python3 -m unittest discover -s modules/api/tests -v
```

## 替换点

FastAPI → 其他框架，OpenAPI 契约不变；认证可换 OIDC/外部 IdP，但会话/CSRF 语义必须保持。