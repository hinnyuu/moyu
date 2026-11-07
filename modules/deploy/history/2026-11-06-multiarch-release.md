---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# 多架构发布

## 改动

- release workflow 构建 amd64+arm64 并拼 manifest。
- 文档同步。

## 影响

- GHCR 提供多架构 tag；未签名。
