---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
  - contracts
  - deploy
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/api/tests -v; python3 modules/deploy/scripts/process_e2e.py; agent-gate --staged
---

# 进程级 E2E 与任务输出下载

## 背景

沙箱没有 Podman，但业务链路可以在进程级验收。E2E 中发现 API 只能下载资产，不能下载任务输出 ZIP，WebUI 无法取回结果。

## 改动

- 新增 `GET /api/v1/jobs/{id}/download`：仅 `succeeded` 任务可下载，返回输出 ZIP。
- API 测试增加“未完成返回 409、成功后下载 PK ZIP”的断言。
- OpenAPI 增加任务输出下载端点。
- 新增 `modules/deploy/scripts/process_e2e.py`：启动 api/worker 子进程，完成登录、上传、创建任务、worker 打包、下载、ZIP/manifest/源资产校验。
- 更新 API 与 deploy 的 docs/module.yaml。

## 影响

- WebUI/部署脚本可以取回打包结果。
- 进程级 E2E 不依赖 Podman，可在当前 aarch64 沙箱运行。
- Podman/Quadlet 仍需 amd64 CI 或具备 KVM 的环境验证。

## 验证

- `python3 -m unittest discover -s modules/api/tests -v`：14 passed。
- `python3 modules/deploy/scripts/process_e2e.py`：PASS（1 个 ZIP 条目，manifest sha256 匹配，源资产未修改）。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。