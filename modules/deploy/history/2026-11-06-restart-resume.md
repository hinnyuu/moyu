---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# API 重启续传 E2E

## 改动

- 新增脚本：上传中断 → API 重启 → 续传 → finish。
- python CI 接入。

## 影响

- 覆盖服务重启续传；文档同步。
