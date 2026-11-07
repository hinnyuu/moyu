---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - deploy
docs_impact: false
docs_reason: 仅修复 smoke 脚本检查方式，部署步骤不变
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: bash -n modules/deploy/scripts/podman_smoke.sh; agent-gate --staged
---

# 修复 Podman smoke 误报容器未运行

## 背景

Podman smoke 报告 `tusd container is not running`，但 `podman ps` 显示 `moyu-smoke-...-tusd` 已 Up。

## 原因

脚本启用了 `set -o pipefail`，并使用：

```bash
podman ps --format '{{.Names}}' | grep -q "..."
```

`grep -q` 匹配后立即退出，`podman ps` 可能收到 SIGPIPE（141），pipefail 让整条管道失败，`!` 将其判为“容器未运行”。这是竞态，所以有时 worker/preview 通过、tusd 失败。

## 改动

- 容器状态改用 `podman inspect --format '{{.State.Running}}' <name>`，不经过管道。
- session JSON 断言改用 shell `case`，不再依赖 `echo | grep -q`。

## 影响

- smoke 容器检查不再受 SIGPIPE/pipefail 影响。

## 验证

- `bash -n modules/deploy/scripts/podman_smoke.sh` 通过。
- 待 `podman`/`podman-arm64` 重跑确认。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
