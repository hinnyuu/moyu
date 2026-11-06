---
date: 2026-11-06
module: contracts
commit: (included in this commit)
---

# OpenAPI 增加分片端点

## 改动

- `/api/v1/uploads/{id}` 增加 `PATCH`，描述 `Upload-Offset` 头、二进制请求体与 204 响应。
- 标注生产由 tusd 处理，该端点为同源/开发模式。

## 影响

- Web 与 API 实现共享同一分片语义。