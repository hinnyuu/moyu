---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules: []
docs_impact: false
docs_reason: 仅修复 CI workflow 步骤
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: python3 -c "import yaml; yaml.safe_load(open('.github/workflows/supply-chain.yml'))"; agent-gate --staged
---

# 修复 supply-chain 回退到 cargo-deny-action

## 背景

清理诊断时工作区回退，把 supply-chain 误改回 EmbarkStudios action，导致再次失败。

## 改动

- 恢复为 taiki-e 安装 cargo-deny + 直接 `cargo deny check`。
- 保持 `contents: read`。

## 影响

- 恢复 supply-chain #18 的成功路径。
