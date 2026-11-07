---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: true
wiki_impact: false
wiki_reason: 用户管理页补充了管理员操作，普通流程不变
breaking: false
tests: npm run typecheck; npm run build; npx playwright test --list; agent-gate --staged
---

# WebUI 用户管理

## 背景

多用户 API 已完成，但 WebUI 没有入口，管理员只能通过 curl 管理用户。

## 改动

- 新增 `Users.tsx`：列表、创建、删除、重置密码。
- 仅 admin 显示“用户”导航。
- API 客户端增加 users/create/delete/reset。
- Playwright 增加用户页 mock E2E（5 个）。
- Web docs 更新。

## 影响

- 管理员可在 WebUI 完成用户管理；operator 不可见。
- 删除自己/最后一个 admin 由 API 拒绝。

## 验证

- typecheck/build 通过；Playwright 列出 5 个用例。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
