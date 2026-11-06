---
date: 2026-11-06
branch: feat/phase1-core-time-rust-ci
commit: (included in this commit)
modules:
  - archive-zip
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/archive-zip/tests -v; agent-gate --staged
---

# archive-zip 阶段 1 最小实现

## 背景

阶段 1 需要一个不依赖媒体格式的 ZIP 写入器，先把“DOS 时间、无时间 extra、原子落盘、可校验”这几条硬约束实现出来。

## 改动

- 新增 Python 包 `modules/archive-zip/src/moyu_archive_zip/`：`dos.py`、`writer.py`、`verify.py`。
- 实现 `ArchiveWriter.add_entry` / `add_file` / `finalize` / `abort`，默认 STORE，可选 DEFLATE。
- 实现 `verify_archive`：中央目录与本地头、DOS 时间一致性、时间类 extra 拒绝、ZIP64 extra、CRC、期望条目比对、未来时间检查。
- 新增 15 个单元测试。
- 新增 `.github/workflows/python.yml`，遍历 `modules/*/tests` 运行 Python 单元测试。
- 更新 archive-zip 的 README、docs、wiki 和 `module.yaml`。

## 影响

- pipeline 现在可以基于稳定接口写 ZIP，不再依赖根目录原型脚本。
- 根目录 `moyu_zip.py` 继续保留为参考实现，未删除。
- manifest 仍由 pipeline 负责，archive-zip 不写 manifest。

## 验证

- `python3 -m unittest discover -s modules/archive-zip/tests -v`：15 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。