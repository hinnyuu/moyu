---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - storage
docs_impact: true
wiki_impact: false
wiki_reason: 仅修复启动并发，不影响运维步骤
breaking: false
tests: python3 -m unittest discover -s modules/storage/tests -v; python3 -m unittest discover -s modules/api/tests -v; agent-gate --staged
---

# 修复多容器同时初始化的 SQLite 锁

## 背景

Podman smoke 在 #26/#27 失败，#28 成功，属于竞态：api、worker、preview 同时初始化 SQLite，`PRAGMA journal_mode=WAL` 遇到 `database is locked`。

## 改动

- `Storage.connect()`：
  - 连接后先设置 `busy_timeout=30000`；
  - WAL 切换遇到 locked 时在 30 秒内退避重试；
  - 重试时关闭半初始化连接。
- 新增 8 线程并发 `ensure_layout` 测试。
- storage docs 增加并发初始化说明。

## 影响

- 五容器同时启动时 SQLite 初始化不再随机失败。
- 其他数据库错误仍返回 `storage_unavailable`。

## 验证

- storage 8 tests 连续运行 3 次通过。
- API 22 tests 通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
