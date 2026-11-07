---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - archive-zip
docs_impact: true
wiki_impact: false
wiki_reason: 大文件验证属于测试/CI，使用方式不变
breaking: false
tests: python3 modules/archive-zip/scripts/large_file_e2e.py; agent-gate --staged
---

# >4GiB ZIP64 实测

## 背景

发布清单最后一项大文件验证：需要一个条目超过 4GiB 的 ZIP64 实测。

## 改动

- 新增 `modules/archive-zip/scripts/large_file_e2e.py`：
  - 创建 4GiB+1KiB 稀疏源文件；
  - STORE 写入 ZIP；
  - 校验 central directory、条目大小与 ZIP 头；
  - 清理临时文件。
- `python` workflow 增加该步骤。
- archive docs、testing、release checklist、module.yaml 更新。

## 影响

- >4GiB 单条目写入/校验已验证；本地 PASS，输出约 4.0GiB，耗时约 20 秒。
- CI 每次 push 会额外占用约 4GiB 临时磁盘；脚本结束后删除。

## 验证

- 本地运行 PASS：
  `size=4294968320 archive=4294968552 elapsed=19.3s`
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
