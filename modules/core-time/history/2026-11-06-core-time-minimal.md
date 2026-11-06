---
date: 2026-11-06
module: core-time
commit: (included in this commit)
---

# core-time 最小实现

## 改动

- 实现 `SourceTime`、`DosTime`、`PlanEntry`、`TimePlan`。
- 实现 `plan_times`：统一 delta、最新文件对齐目标、DOS 2 秒取整、范围/溢出校验。
- 实现 `dos_from_unix` 和 `civil_from_days`，固定 UTC offset，不依赖系统时区。
- 增加 5 个 Rust 单元测试。
- 增加 `.github/workflows/rust.yml`。
- 更新 core-time docs/wiki/README 和 Rust workspace 文档。

## 影响

- 第一阶段时间核心可被后续 pipeline 使用。
- 本地沙箱无 cargo，编译验证交给 GitHub Actions。
