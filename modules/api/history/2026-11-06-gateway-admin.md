---
date: 2026-11-06
module: api
commit: (included in this commit)
---

# 网关管理接口与客户端

## 改动

- 新增 `GatewayAdminClient` 与 `GatewayAdminError`。
- token rotate/get/revoke、证书 reload/status 从 501 改为真实实现。
- token 明文只返回一次；GET 只返回元数据。
- 新增 `test_gateway_admin.py`（4 个测试），API 测试更新网关代理与 CSRF。

## 影响

- WebUI 可完成 token 轮换与证书重载。
- gateway 未启用返回 409；token 缺失返回 503；不可达返回 502。
