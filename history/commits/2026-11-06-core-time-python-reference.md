---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - core-time
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/core-time/tests -v; agent-gate --staged
---

# core-time Python 参考实现

## 背景

api/worker/pipeline 使用 Python，需要一个与 Rust `moyu-core` 语义一致的时间计划实现，避免服务端重复写时间算法。

## 改动

- 新增 `modules/core-time/python/moyu_core_time/`：`SourceTime`、`DosTime`、`PlanEntry`、`TimePlan`、`plan_times`、`dos_from_unix`、`civil_from_days`、`floor_dos_second`。
- 错误使用 `TimeError.code`：`empty`、`target_not_later`、`dos_out_of_range`、`overflow`。
- 新增 8 个 Python 单元测试，覆盖 DOS 字、公历转换、固定 offset、相对时间计划与错误分支。
- 更新 core-time 的 README、docs、wiki 和 `module.yaml`。

## 影响

- Python 服务可以直接复用 core-time 契约，不再各自实现 delta/DOS 换算。
- Rust 实现仍是 gateway/WASM 的规范实现；两套实现必须通过同一套时间向量。
- 固定 UTC offset 由调用方传入，模块不依赖系统时区。

## 验证

- `python3 -m unittest discover -s modules/core-time/tests -v`：8 passed。
- `cargo test --workspace`：5 passed（Rust）。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。