---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# 同步网关 token 路径

## 改动

- smoke 配置与脚本把 gateway token 写到 `/config/secrets`。
- 部署文档 secret 清单更新。

## 影响

- Podman smoke 中 api 可写、gateway 可读同一 token 文件。
