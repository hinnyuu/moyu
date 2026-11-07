---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - archive-zip
docs_impact: true
wiki_impact: false
wiki_reason: 仅补 ZIP64 条目数测试，使用方式不变
breaking: false
tests: python3 -m unittest discover -s modules/archive-zip/tests -v; agent-gate --staged
---

# ZIP64 65536 条目测试

## 背景

发布清单列 >65535 条目未验证；archive-zip 依赖 Python zipfile 的 ZIP64 EOCD，需要行为测试。

## 改动

- 新增测试：写 65536 个 STORE 条目，校验 central directory、EOCD 与条目数。
- archive docs 更新测试覆盖。

## 影响

- 确认 writer/verifier 能处理超过 65535 条目。
- >4GiB 单文件仍未实测（受沙箱磁盘/时间限制）。

## 验证

- archive-zip：16 tests，6.1s。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
