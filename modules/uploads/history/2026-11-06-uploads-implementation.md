---
date: 2026-11-06
module: uploads
commit: (included in this commit)
---

# uploads 阶段 2 最小实现

## 改动

- 新增 `src/moyu_uploads/`：会话创建、偏移查询、顺序分片、完成、取消、过期。
- 元数据写入 `meta.json`；偏移/状态复用 storage 的 `upload_sessions` 表。
- 完成时调用 `AssetStore.register_asset`，随后删除会话目录与数据库行。
- 新增 7 个单元测试。

## 影响

- 分片必须按序；偏移不一致或超长直接失败。
- 超过上传上限或配额不足时不创建/不追加。
- tus HTTP 路由与上传 token 尚未实现。