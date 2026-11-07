---
date: 2026-11-06
module: config
commit: (included in this commit)
---

# 预览服务地址配置

## 改动

- `preview.serviceUrl` 加入 schema 与默认值（默认空字符串）。

## 影响

- 为空时 API 使用进程内 provider；部署时指向 Pod 内 preview。
