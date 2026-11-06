# core-time

时间策略、目标时间映射、DOS/EXIF/QuickTime/Matroska 时间换算，以及 target-neutral 的 Rust core crate。

- 当前状态：v0.0.1 阶段 1 最小实现（Rust + Python 参考实现）。
- 依赖：contracts
- 接口：TimePolicy、PackPlan 时间字段；Rust `moyu-core`、Python `moyu_core_time`
- 实现：`rust/`、`python/`
- 测试：`rust/src/lib.rs` 单元测试、`tests/test_core_time.py`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。