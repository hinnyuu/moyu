---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - preview
  - web
docs_impact: false
docs_reason: 仅修正 E2E 测试数据与错误映射，行为契约未变化
wiki_impact: false
wiki_reason: 用户操作未变化
breaking: false
tests: python3 -m unittest discover -s modules/preview/tests -v; python3 -m unittest discover -s modules/api/tests -v; agent-gate --staged
---

# 修复 fullstack E2E 的预览 500 与选择器冲突

## 背景

`fullstack` 第二次失败有两个独立问题：

1. `getByRole("button", { name: "任务" })` 同时匹配“任务”和“创建任务”，strict mode 报错。
2. 测试内嵌的 1x1 PNG base64 实际是损坏数据，预览接口返回 500。

## 改动

- Web E2E：
  - “任务”导航按钮改为 `exact: true`；
  - 使用 Pillow 生成的有效 1x1 PNG base64。
- preview：
  - 图像解码/编码异常统一映射为 `PreviewError("preview_failed")`，不再抛 500；
  - 新增损坏图片返回 415 的服务测试。

## 影响

- 损坏图片现在返回 415，而不是未处理异常。
- fullstack E2E 使用有效 PNG，可继续到创建任务与任务成功。

## 验证

- preview 12 tests（1 个 HLS 跳过）；API 22 tests。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
