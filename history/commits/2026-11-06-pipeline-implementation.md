---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - pipeline
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/pipeline/tests -v; agent-gate --staged
---

# pipeline 阶段 1 最小闭环

## 背景

core-time、media-metadata、archive-zip 已有最小实现，需要一个编排层把“输入文件 → 时间计划 → 元数据改写 → ZIP → manifest → 校验”串起来。

## 改动

- 新增 `modules/pipeline/src/moyu_pipeline/`：`PackInput`、`pack`、`resolve_offset`、`PackError`。
- 流水线：stat → `plan_times` → 元数据补丁/materialize → `ArchiveWriter` → 源文件复查 → manifest → 二次校验。
- manifest 记录目标时间、delta、每条目的 DOS/元数据字段、归档 sha256。
- 失败时清理 `.part` 与 materialize 临时文件。
- 新增 7 个集成测试。
- 更新 pipeline 的 README、docs、wiki 和 `module.yaml`。

## 影响

- 阶段 1 的最小打包闭环可用，worker 可以直接调用 `pack`。
- 仍不包含 HTTP、任务存储、上传、预览和 WebUI。
- Python 模块之间通过 `PYTHONPATH` 或安装包装配，尚未生成打包元数据。

## 验证

- `python3 -m unittest discover -s modules/pipeline/tests -v`：7 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。