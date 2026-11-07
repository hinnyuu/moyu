---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules: []
docs_impact: false
docs_reason: 仅移除临时诊断步骤与写权限
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: python3 -c "import yaml; yaml.safe_load(open('.github/workflows/fullstack.yml')); yaml.safe_load(open('.github/workflows/supply-chain.yml'))"; agent-gate --staged
---

# 移除 CI 临时诊断

## 背景

fullstack、supply-chain、agent-gate 已恢复绿色，临时失败日志提交不再需要。

## 改动

- 移除 fullstack/supply-chain 的失败日志自动提交。
- 权限恢复为 `contents: read`。
- supply-chain 保留 taiki-e 安装 cargo-deny + 直接运行。

## 影响

- 工作流不再向 main 自动提交诊断文件。
