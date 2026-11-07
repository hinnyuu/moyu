---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
  - contracts
docs_impact: true
wiki_impact: false
wiki_reason: 多用户/重置/限流属于管理能力，普通登录流程不变
breaking: false
tests: python3 -m unittest discover -s modules/api/tests -v; agent-gate --staged
---

# 多用户、密码重置与登录限流

## 背景

发布前缺口：单管理员、无密码找回、无速率限制。

## 改动

- AuthManager 支持 users 字典与 admin/operator 角色，兼容旧 admin state。
- 新增用户管理：list/create/delete/change password；保护最后一个管理员与自身删除。
- bootstrap token 可重置 admin 密码。
- 新增内存登录限流：默认 5 次/5 分钟/IP，成功登录清零。
- Session 增加 role；API 增加用户接口与 reset 接口。
- OpenAPI/API docs/release notes/checklist 更新。

## 影响

- 管理员可创建运营账号；运营账号不能管理用户。
- 自己改密码需要原密码；管理员可重置他人。
- 限流为进程内，重启清零；多副本需外部限流。

## 验证

- API 27 tests 通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
