---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: true
wiki_impact: false
wiki_reason: 仅更新发布清单与测试状态，操作流程不变
breaking: false
tests: agent-gate --staged
---

# 发布候选文档收敛

## 背景

截图基线、视频 E2E、多架构发布、供应链检查、用户管理均已完成后，发布清单仍把它们列为未完成。

## 改动

- release checklist：标记截图基线、视频 E2E、多架构、供应链为已完成；剩余为故障注入/长时测试与镜像签名。
- release notes：移除截图基线未完成项。
- Web docs：mock E2E 更新为 6 个，截图基线已生成。
- README 状态更新。

## 影响

- 文档只列真实剩余限制。

## 验证

- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
