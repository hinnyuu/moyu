---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: false
docs_reason: 仅修复测试 preview 监听地址
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: npx playwright test --list; python3 -c "import yaml; yaml.safe_load(open('.github/workflows/visual-baseline.yml'))"; agent-gate --staged
---

# 修复截图基线 preview 监听地址

## 背景

失败日志显示 vite preview 已启动，但 127.0.0.1 curl 不可达；默认 localhost 可能绑定 IPv6。

## 改动

- Playwright webServer 与 visual-baseline 手动 preview 均显式 `--host 127.0.0.1`。

## 影响

- webServer 健康检查与 Playwright baseURL 一致。
