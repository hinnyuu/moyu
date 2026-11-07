---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules: []
docs_impact: false
docs_reason: 仅调整 CI 检查范围，契约与文档事实不变
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: cargo deny check licenses bans sources; agent-gate --staged
---

# cargo-deny 改为 licenses/bans/sources

## 背景

supply-chain 的 cargo-deny 偶发失败，而 cargo-audit 已稳定成功；advisory DB 拉取依赖网络。

## 改动

- cargo-deny 只检查 licenses/bans/sources。
- 漏洞 advisories 继续由 cargo-audit 覆盖。

## 影响

- 避免 advisory DB 网络波动导致 CI 红。
- 检查覆盖不降低：审计仍由 cargo-audit 执行。
