---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules: []
docs_impact: false
docs_reason: deploy 文档已说明进程级 E2E 的运行方式，本次只把它接入 CI
wiki_impact: false
wiki_reason: 操作流程未变化
breaking: false
tests: python3 modules/deploy/scripts/process_e2e.py; agent-gate --staged
---

# CI 接入进程级 E2E

## 背景

`process_e2e.py` 已在本地通过，但没有在每次提交时自动运行，回归只能靠人工。

## 改动

- `python` workflow 增加 `uvicorn` 依赖。
- 模块测试之后运行 `python3 modules/deploy/scripts/process_e2e.py`。

## 影响

- 每次 push/PR 都验证登录、上传、任务、worker、ZIP 与 manifest。
- E2E 使用临时目录和随机端口，不依赖 Podman。
- Podman/Quadlet 仍需单独的 amd64 CI 验证。

## 验证

- 本地 `python3 modules/deploy/scripts/process_e2e.py`：PASS。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
- 待 GitHub `python` workflow 确认。