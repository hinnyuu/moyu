# core-time 模块文档

状态：v0.0.1 阶段 1 最小实现（Rust + Python 参考实现）。

## 职责

时间策略、目标时间映射、DOS/EXIF/QuickTime/Matroska 时间换算，以及 target-neutral 的 Rust core crate。

输入源文件 mtime 和目标时间，输出统一的 TimePlan。所有文件使用同一个 delta，保持相对顺序；最新文件对齐目标时间；DOS 时间按 2 秒向下取整。时区使用 IANA 名称，内部计算以 epoch 为准。Rust crate 只放目标无关逻辑，不引入 tokio、文件系统、TLS。

## 非职责

不做文件 I/O、不读媒体元数据、不写 ZIP、不访问数据库。

## 依赖

contracts

## 接口

TimePolicy、PackPlan 时间字段；Rust `moyu-core`

## 失败模式

目标时间早于最新源 mtime、DOS 时间越界、时区无效。

## 测试

固定时间向量、跨时区、亚秒间隔、2038/2107 边界。

## 替换点

纯函数实现可替换；Rust 与 Python 实现必须通过同一套时间向量 conformance。

## 最小实现

`moyu-core` 已实现第一阶段时间策略：

- `SourceTime { id, mtime_ns }`
- `DosTime { year, month, day, hour, minute, second }`
- `TimePlan { target_epoch, delta_ns, utc_offset_seconds, entries }`
- `plan_times(sources, target_epoch, utc_offset_seconds)`：
  - 空输入报错；
  - 目标时间必须晚于最新源 mtime；
  - 所有文件使用同一个 delta；
  - 最新文件落在目标 epoch；
  - DOS 秒按 2 秒向下取整；
  - 1980–2107 范围校验；
  - 溢出时返回 `Overflow`。
- `dos_from_unix` 使用固定 UTC offset，不依赖系统时区/时区数据库；IANA 时区解析由上层配置层负责。

沙箱没有 cargo/rustc 时以 GitHub Actions 为准；当前本地与 CI 均已验证。

## Python 参考实现

`python/moyu_core_time/` 是同一契约的 Python 实现，供 api/worker/pipeline 使用：

- 导出 `SourceTime`、`DosTime`、`PlanEntry`、`TimePlan`；
- `plan_times(sources, target_epoch, utc_offset_seconds)`；
- `dos_from_unix(epoch_seconds, utc_offset_seconds)`；
- `civil_from_days`、`floor_dos_second`；
- 错误通过 `TimeError.code` 区分：`empty`、`target_not_later`、`dos_out_of_range`、`overflow`。

Python 与 Rust 实现必须通过同一套时间向量；当前 `tests/test_core_time.py` 覆盖 DOS 字、公历转换、固定 offset、相对时间计划与错误分支。
