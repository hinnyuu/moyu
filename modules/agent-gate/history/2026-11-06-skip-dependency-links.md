---
date: 2026-11-06
module: agent-gate
commit: (included in this commit)
---

# 链接检查跳过依赖与构建目录

## 改动

- `check_links` 跳过 `.git`、`node_modules`、`dist`、`target`、`.venv`、`__pycache__`。
- 新增测试：node_modules 内的失效链接不报错。

## 影响

- Web 依赖安装后，本地门禁不再扫描第三方 README。
- 项目自身 Markdown 仍全部检查。