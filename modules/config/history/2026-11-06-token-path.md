---
date: 2026-11-06
module: config
commit: (included in this commit)
---

# 网关 token 默认路径

## 改动

- `gateway.reload.api.tokenFile` 默认从 `/run/secrets/gateway_reload_token` 改为 `/config/secrets/gateway_reload_token`。

## 影响

- api（config 读写）可以轮换 token，gateway（config 只读）可以读取。
- bootstrap token 仍在 `/run/secrets`。
