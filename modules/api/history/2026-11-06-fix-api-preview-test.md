---
date: 2026-11-06
module: api
commit: (included in this commit)
---

# 修复预览测试缓存目录

## 改动

- 测试 setUp 将 `preview.cacheDir` 覆盖为临时目录后再创建 app。

## 影响

- CI runner 不再尝试创建 `/data/preview`。
- API 认证、配置、上传、任务测试不变。