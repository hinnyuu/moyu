---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules: []
docs_impact: false
docs_reason: 仅 CI 诊断与临时日志清理
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: python3 -c "import yaml; yaml.safe_load(open('.github/workflows/fullstack.yml')); yaml.safe_load(open('.github/workflows/supply-chain.yml'))"; agent-gate --staged
---

# CI 失败日志诊断与清理

## 背景

fullstack 与 supply-chain 持续失败，公开 API 无法读取详细日志；visual-baseline 基线已生成。

## 改动

- 删除 `baseline-error.log` 与 visual-baseline 的失败日志自动提交步骤。
- fullstack/supply-chain 失败时把日志提交到仓库便于诊断。
- supply-chain 改用 taiki-e 安装 cargo-deny 后直接运行，便于捕获输出。

## 影响

- 临时授予 contents: write；诊断完成后移除。
- 基线文件已保留。
