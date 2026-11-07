---
date: 2026-11-06
module: api
commit: (included in this commit)
---

# 任务输出下载端点

## 改动

- 新增 `GET /api/v1/jobs/{id}/download`，仅成功任务可下载。
- 输出名取 job request 的 `output_name`，缺省 `delivery.zip`。
- 测试覆盖未完成 409 与成功下载。

## 影响

- WebUI 与自动化脚本可以取回打包结果。
- 下载路径仍由 storage 的 output_path 限制在数据根内。