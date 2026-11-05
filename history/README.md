# 项目 History

本目录是**只追加**的项目历史。它记录“什么时候、为什么、改了什么、影响是什么”，不记录当前接口规范。

## 规则

- 每个提交一个 `commits/<日期>-<slug>.md`。
- 每个 ADR 一个 `decisions/ADR-XXXX-<slug>.md`。
- 版本发布记录放 `releases/`，v0.0.1 之后才有。
- 不修改旧条目；需要更正时追加新条目并链接旧条目。
- 不把完整当前设计复制到 history；用链接指向 docs。
- 不把历史流水账写进 docs 或 wiki。

## 提交记录建议格式

```yaml
---
date: 2026-11-06
branch: draft/v0.0.1-architecture
commit: pending
modules: [docs, contracts, gateway, ...]
docs_impact: true
wiki_impact: true
breaking: false
tests: documentation-only
---

# 标题

## 背景
## 改动
## 影响
## 验证
## 后续
```

## 目录

- `commits/`：每个提交的时间线。
- `decisions/`：ADR，记录取舍和替代方案。
- `releases/`：版本发布说明（v0.0.1 之后）。
- `index.md`：人类可读索引。