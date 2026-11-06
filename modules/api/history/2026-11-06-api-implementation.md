---
date: 2026-11-06
module: api
commit: (included in this commit)
---

# api 阶段 2 最小实现

## 改动

- 新增 `src/moyu_api/`：`create_app`、`AuthManager`、`Session`、`AuthError`。
- 认证：bootstrap token 初始化、PBKDF2 密码、HMAC 签名 cookie、CSRF 双提交。
- 接口：健康、会话、配置读写、上传会话/完成、任务创建/查询/取消/SSE、资产下载、预览、网关管理占位。
- 错误统一为 `{code,message,details,module}`。
- 新增 14 个单元测试（7 认证 + 7 API）。
- 更新 api 的 README、docs、wiki 和 `module.yaml`，并补充 OpenAPI 中的认证/上传端点。

## 影响

- WebUI 可以通过会话 cookie + CSRF 调用 API。
- 网关管理接口仍返回 501，等待 gateway 客户端。
- tus 分片仍由 tusd 负责；API 只创建会话和完成入库。
- 认证文件路径由装配代码提供，未写入普通配置。

## 验证

- `python3 -m unittest discover -s modules/api/tests -v`：14 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。