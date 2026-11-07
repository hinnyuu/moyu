---
date: 2026-11-06
module: web
commit: (included in this commit)
---

# 批量队列与断点续传

## 改动

- 新增 `queue.ts` 与 IndexedDB Blob 缓存。
- Upload 页支持多文件、暂停/恢复、刷新续传。
- 新增 4 个 Vitest 测试；CI 增加 `npm test`。

## 影响

- 浏览器数据清理会导致本地缓存丢失，需要重新添加文件。
- WASM 客户端打包仍未接入。
