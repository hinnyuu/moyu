---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
  - contracts
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/api/tests -v; agent-gate --staged
---

# api 阶段 2 最小实现

## 背景

配置、存储、上传、预览和 worker 已可用，需要一个带认证的 HTTP 入口把这些能力暴露给浏览器和部署工具。

## 改动

- 新增 `modules/api/src/moyu_api/`：`create_app`、`AuthManager`、`Session`、`AuthError`。
- 认证：bootstrap token 初始化管理员、PBKDF2-HMAC-SHA256 密码、HMAC 签名会话 cookie、绑定会话的 CSRF token。
- 接口：健康、会话、配置读写、上传会话/完成、任务创建/查询/取消/SSE、资产下载、预览、网关管理占位。
- 错误响应统一为 `{code,message,details,module}`；请求体大小限制。
- OpenAPI 补充 `GET /auth/session`、`GET /uploads/{id}`、`POST /uploads/{id}/finish` 与认证描述。
- 新增 14 个单元测试（7 认证 + 7 API）。
- Python CI 增加 fastapi/httpx 依赖。

## 影响

- WebUI 与部署工具可以通过会话 cookie + CSRF 调用 API。
- 网关管理接口返回 501，等待 gateway 客户端。
- tus 分片仍由 tusd 负责；API 只创建会话与完成入库。
- 单管理员、无密码找回、无速率限制；TLS 部署需设置 `cookie_secure=True`。

## 验证

- `python3 -m unittest discover -s modules/api/tests -v`：14 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。