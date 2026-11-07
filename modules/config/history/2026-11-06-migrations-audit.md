---
date: 2026-11-06
module: config
commit: (included in this commit)
---

# schema 迁移与审计

## 改动

- 新增逐版本迁移框架、迁移备份与原子写回。
- 新增 SQLite 审计表 `state/audit.db`。
- `write` 记录 actor/module/revision/result。
- 新增 `audit()` 与 4 个测试。

## 影响

- 当前 schemaVersion 仍为 1；迁移路径通过注入 1→2 测试验证。
- 只读模式遇到待迁移配置返回 `migration_required`。
