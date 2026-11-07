---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
  - deploy
docs_impact: true
wiki_impact: false
wiki_reason: 真实后端 E2E 属于 CI，不改变用户操作步骤
breaking: false
tests: bash -n modules/deploy/scripts/fullstack_e2e.sh; npm run typecheck; agent-gate --staged
---

# 真实后端 Playwright E2E

## 背景

发布清单要求真实后端联动的 Playwright；此前只有 mock API 的前端 E2E。

## 改动

- 新增 `playwright.fullstack.config.ts` 与 `tests/fullstack/flow.fullstack.ts`：
  - 首次 bootstrap 登录；
  - 上传 PNG 并等待完成；
  - 创建打包任务；
  - 任务页等待 `succeeded`；
  - 切换主题并检查无 pageerror。
- 新增 `modules/deploy/scripts/fullstack_e2e.sh`：
  - 生成临时 config/data/secret；
  - 启动 api/worker；
  - 使用构建后的 Web 运行 Playwright。
- 新增 `fullstack` workflow。
- 更新 Web/deploy/testing/release checklist 文档与 module.yaml。

## 影响

- 真实 UI → API → worker → ZIP 状态链路进入 CI。
- 仍未覆盖明暗主题截图基线与对比度自动检查。

## 验证

- 脚本语法与 Web typecheck 通过。
- 本地无 Chromium，未运行 E2E；待 `fullstack` workflow 验证。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
