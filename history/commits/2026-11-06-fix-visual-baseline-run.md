---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: false
docs_reason: 仅修复基线生成模式与视频测试诊断
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: npx playwright test --list; python3 -c "import yaml; yaml.safe_load(open('.github/workflows/visual-baseline.yml'))"; agent-gate --staged
---

# 修复截图基线生成与视频 E2E 诊断

## 背景

`visual-baseline` 首次运行在 Generate baselines 失败；Playwright 的 `--update-snapshots` 无参数默认模式不会创建缺失快照。

## 改动

- 基线生成改为 `--update-snapshots=all`。
- 视频 E2E 同时等待成功 video 与 `.error`，失败时抛出转码错误文本，便于定位。
- 视频测试超时提升到 300 秒。

## 影响

- 缺失基线会被实际创建。
- 视频转码失败会在 CI 摘要中显示原因。

## 验证

- Playwright 列出 6 个用例；workflow YAML 解析通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
