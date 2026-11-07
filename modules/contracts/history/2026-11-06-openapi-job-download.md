---
date: 2026-11-06
module: contracts
commit: (included in this commit)
---

# OpenAPI 增加任务输出下载

## 改动

- 增加 `GET /api/v1/jobs/{id}/download`，描述 200/409/404。

## 影响

- API 与 Web/部署客户端共享同一输出下载契约。