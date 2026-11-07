---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
  - deploy
docs_impact: false
docs_reason: 仅修正 E2E 流程与超时，文档描述不变
wiki_impact: false
wiki_reason: 用户操作未变化
breaking: false
tests: bash -n modules/deploy/scripts/fullstack_e2e.sh; agent-gate --staged
---

# 修复 fullstack E2E 超时

## 背景

`fullstack` CI 超时。日志显示登录、上传、finish 都成功，但没有创建任务。

## 原因

上传完成后页面出现“创建打包任务”，但资产下拉默认空；测试未选择资产就点击“创建任务”，按钮处于禁用状态，随后等待成功提示直到超时。

## 改动

- 测试先等待“创建打包任务”标题，再选择第一个资产。
- fullstack 配置超时提升到 90 秒。
- 启动 api/worker 时设置 `PYTHONUNBUFFERED=1`，失败时日志不再为空。

## 影响

- E2E 覆盖真实“选择资产 → 创建任务 → worker 成功”路径。

## 验证

- 脚本语法检查通过。
- 本地无 Chromium，待 `fullstack` workflow 验证。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
