---
date: 2026-11-06
module: storage
commit: (included in this commit)
---

# 任务领取与恢复

## 改动

- `JobStore.claim_next()`：条件更新 `queued → running`，避免多个 worker 重复领取。
- `JobStore.recover_stale()`：把 `running`/`verifying` 重置为 `queued`，记录重启原因。
- 更新模块 docs 中的接口与恢复语义。

## 影响

- worker 可以安全地单次领取任务并在重启后恢复。
- 状态机校验仍然存在；这两个方法分别用于领取和显式恢复。