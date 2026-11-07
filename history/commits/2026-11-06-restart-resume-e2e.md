---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - deploy
docs_impact: true
wiki_impact: false
wiki_reason: E2E 属于 CI/验收，不改变用户操作
breaking: false
tests: python3 modules/deploy/scripts/restart_resume_e2e.py; agent-gate --staged
---

# API 重启续传 E2E

## 背景

发布清单列“服务重启续传”未验证；uploads 已有存储层跨实例测试，但缺少真实 API 进程重启验证。

## 改动

- 新增 `modules/deploy/scripts/restart_resume_e2e.py`：
  - 启动 API、创建上传会话、上传 4 字节；
  - 终止并重启 API；
  - 重新登录，读取 offset=4；
  - 续传剩余字节、finish、下载校验。
- `python` workflow 增加该步骤。
- deploy/testing/release checklist 文档更新。

## 影响

- 上传会话、offset、SQLite、认证状态跨 API 重启可恢复。
- >4GiB 单文件仍未验证。

## 验证

- 本地运行：PASS（offset_after_restart=4，bytes=10）。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
