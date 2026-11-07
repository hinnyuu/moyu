---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
  - contracts
  - deploy
docs_impact: true
wiki_impact: false
wiki_reason: token 审计属于管理细节，普通操作流程不变
breaking: false
tests: python3 -m unittest discover -s modules/api/tests -v; agent-gate --staged
---

# 网关 token 元数据与审计

## 背景

发布前缺口：token 只有文件，不记录创建/轮换/最近使用/审计。

## 改动

- 新增 `TokenStore`（SQLite `config/state/gateway_token.db`）：
  - meta：created_at、rotated_at、last_used_at、fingerprint_sha256、label；
  - audit：rotate/revoke/use 记录。
- `GatewayAdminClient`：
  - rotate/revoke 写库并审计；
  - cert_status/reload 后记录 last_used 与 use 审计；
  - token_metadata 合并文件与 DB 字段。
- API 新增 `GET /api/v1/admin/gateway/token/audit`。
- 契约/API/deploy 文档更新，移除“token 审计待补”。

## 影响

- token 明文仍只在文件中；数据库只存 SHA-256 指纹与元数据。
- 审计库随 `/config` 持久化。

## 验证

- API 22 tests 通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
