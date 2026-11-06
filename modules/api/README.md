# api

HTTP API、认证、任务/上传接口、Web 静态文件、管理接口聚合。

- 当前状态：v0.0.1 阶段 2 最小实现（FastAPI + 会话认证）。
- 依赖：contracts, pipeline, storage, uploads, preview, config
- 接口：OpenAPI；GatewayAdmin 客户端；Job/Asset/Config API
- 实现：`src/moyu_api/`
- 测试：`tests/test_auth.py`、`tests/test_api.py`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。