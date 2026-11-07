---
date: 2026-11-06
module: gateway
commit: (included in this commit)
---

# 管理路径、证书哈希与常量时间 token

## 改动

- 新增 `/admin/cert/reload`、`/admin/cert/status` 别名。
- 状态与重载响应增加 `cert_sha256`。
- `CertStore::reload` 同步更新哈希。
- token 比较使用 `subtle` 常量时间。
- 新增 `sha2`、`subtle` 依赖。

## 影响

- API 可以按契约路径调用管理 API。
- 证书哈希可用于状态展示与轮换确认；serial/not_after 仍未解析。
