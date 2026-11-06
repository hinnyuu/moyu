# uploads

tus 断点续传会话、偏移量、完成钩子、入库。

- 当前状态：v0.0.1 阶段 2 最小实现（Python）。
- 依赖：contracts, storage
- 接口：UploadSessionStore；tusd 完成钩子
- 实现：`src/moyu_uploads/`
- 测试：`tests/test_uploads.py`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。