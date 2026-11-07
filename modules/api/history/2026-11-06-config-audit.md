---
date: 2026-11-06
module: api
commit: (included in this commit)
---

# 配置审计接口

## 改动

- 新增 `GET /api/v1/config/audit`，返回 config 审计记录。
- 测试在配置写入后断言 `write` 审计。

## 影响

- WebUI/运维可以查看运行配置修改历史。
