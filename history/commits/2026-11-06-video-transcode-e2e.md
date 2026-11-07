---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
  - deploy
docs_impact: true
wiki_impact: false
wiki_reason: 新增测试步骤，不改变用户操作
breaking: false
tests: bash -n modules/deploy/scripts/fullstack_e2e.sh; npm run typecheck; npx playwright test --list; agent-gate --staged
---

# 真实视频转码 E2E

## 背景

发布清单要求视频转码成功路径自动化；此前只验证隔离与回退。

## 改动

- fullstack Playwright 增加视频用例：
  - CI 用 ffmpeg 生成 1 秒 160x90 MP4；
  - 上传、点击“本地视频转码”，等待 blob 视频。
- fullstack workflow 安装 ffmpeg。
- 脚本在可用时导出 `MOYU_E2E_VIDEO`。
- 文档更新。

## 影响

- CI 验证 ffmpeg.wasm 实际转码成功路径。
- 无 ffmpeg 的环境跳过该用例。

## 验证

- 脚本语法、Web typecheck、Playwright 列用例通过。
- 待 `fullstack` CI 实际执行。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
