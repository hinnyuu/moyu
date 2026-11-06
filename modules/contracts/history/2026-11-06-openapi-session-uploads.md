---
date: 2026-11-06
module: contracts
commit: (included in this commit)
---

# OpenAPI 补充会话与上传端点

## 改动

- `GET /api/v1/auth/session`：读取当前会话与 CSRF token。
- `GET /api/v1/uploads/{id}`：读取上传会话。
- `POST /api/v1/uploads/{id}/finish`：完成上传并登记资产。
- 登录描述补充 bootstrap token、密码与 `X-CSRF-Token` 语义。

## 影响

- OpenAPI 与 api 实现保持一致。
- 分片传输仍由 tusd 负责，未新增分片端点。