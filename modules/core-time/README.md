# core-time

时间策略、目标时间映射、DOS/EXIF/QuickTime/Matroska 时间换算，以及 target-neutral 的 Rust core crate。

- 当前状态：v0.0.1 架构草稿，尚未实现。
- 依赖：contracts
- 接口：TimePolicy、PackPlan 时间字段；Rust `moyu-core`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。
- Phase 0 已建立 Rust core crate 骨架；业务实现尚未开始。

- 第一阶段已实现 `plan_times` / `dos_from_unix`；由 Rust CI 验证。
