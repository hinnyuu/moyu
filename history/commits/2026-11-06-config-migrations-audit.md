---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - config
  - api
  - contracts
docs_impact: true
wiki_impact: false
wiki_reason: 迁移与审计只影响配置维护者，未改变普通用户操作流程
breaking: false
tests: python3 -m unittest discover -s modules/config/tests -v; python3 -m unittest discover -s modules/api/tests -v; python3 modules/deploy/scripts/process_e2e.py; agent-gate --staged
---

# config schema 迁移与审计

## 背景

发布前审计发现 config 契约要求 schemaVersion 迁移、迁移前备份和审计表，但实现缺失。

## 改动

- 新增 `migrations.py`：`Migration`、`CURRENT_VERSION`、注册表与逐版本校验。
- `ConfigProvider` 支持 `migrations` / `current_version`：
  - 低于当前版本时备份并逐版本迁移；
  - `migration_missing`、`migration_required`、`schema_newer` 错误；
  - 迁移后原子写回并记录 `migrate` 审计。
- 新增 `state/audit.db` 的 `config_audit` 表；`write` 记录 `write` 审计。
- 新增 `audit(limit)` 与 `GET /api/v1/config/audit`。
- 新增 4 个 config 测试；API 测试增加审计断言。
- 更新 config/api docs 与 config 契约。

## 影响

- 默认版本仍为 1，当前不触发真实迁移；框架已用测试迁移 1→2 验证。
- 只读 worker 遇到待迁移配置会失败，需 api 先完成迁移。
- 审计库随 config 目录持久化。

## 验证

- config 15 tests、API 18 tests：通过。
- 进程级 E2E：PASS。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
