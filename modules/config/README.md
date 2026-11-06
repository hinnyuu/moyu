# config

配置目录加载、schema 校验、默认值、原子写入、迁移、last-known-good 和变更审计。

- 当前状态：v0.0.1 阶段 2 最小实现（Python）。
- 依赖：contracts
- 接口：ConfigProvider：load / validate / write / last_known_good
- 实现：`src/moyu_config/`
- 测试：`tests/test_config.py`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。