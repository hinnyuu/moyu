---
date: 2026-11-06
module: api
commit: (included in this commit)
---

# 分片上传端点

## 改动

- 新增 `PATCH /api/v1/uploads/{id}`，tus 兼容偏移语义。
- 中间件跳过上传分片路径的大小限制。
- API 测试改用 HTTP 分片上传。

## 影响

- 生产可继续用 tusd；开发/同源部署可直接上传。
- 分片必须是 `application/offset+octet-stream`，且偏移量匹配。