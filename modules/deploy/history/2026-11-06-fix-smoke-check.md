---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# 修复 smoke 容器检查

## 改动

- 用 podman inspect 代替 ps|grep -q。
- session JSON 用 shell case 断言。

## 影响

- 消除 pipefail/SIGPIPE 导致的误报。
