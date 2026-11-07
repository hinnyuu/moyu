---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules: []
docs_impact: true
wiki_impact: false
wiki_reason: 供应链检查属于 CI，不改变用户操作
breaking: false
tests: cargo deny check licenses bans sources; python3 -c "import yaml; yaml.safe_load(open('.github/workflows/supply-chain.yml'))"; agent-gate --staged
---

# cargo-deny / cargo-audit 接入

## 背景

发布清单最后一项供应链缺口：cargo deny/audit 未接入。

## 改动

- 新增 `deny.toml`：许可证白名单、bans、sources。
- 新增 `supply-chain` workflow：
  - cargo-deny check；
  - cargo-audit。
- testing/release checklist/发布说明更新。

## 影响

- 依赖许可证、禁用依赖、来源和已知漏洞进入 CI。
- cargo-deny 的 advisory DB 需要访问 GitHub；本地沙箱无法拉取，已在本地验证 licenses/bans/sources。

## 验证

- 本地 `cargo deny check licenses bans sources`：通过（有未使用许可证白名单警告）。
- workflow YAML 解析通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
