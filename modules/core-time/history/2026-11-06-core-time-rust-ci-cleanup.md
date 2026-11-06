---
date: 2026-11-06
module: core-time
commit: (included in this commit)
---

# core-time 的 Rust CI 清理

## 改动

- `second % 2 != 0` 改为 `!second.is_multiple_of(2)`，满足 clippy。
- 测试中删除多余的 `i64::from` 转换。
- 修正 `converts_epoch_to_dos` 的日期断言：1980-01-02 的 DOS 日期字为 34。
- 按 rustfmt 重新排版，补齐文件末尾换行。

## 影响

- 时间算法与接口不变，仅测试与风格调整。
- 5 个单元测试、clippy、fmt 全部通过。