---
date: 2026-11-06
module: config
commit: (included in this commit)
---

# 增加 gateway upstream 配置

## 改动

- `gateway.schema.json` 增加必填 `upstream.url`。
- 默认 gateway 配置增加 `upstream: {url: "http://api"}`。
- 更新配置文档中的 gateway 示例。

## 影响

- gateway 必须明确上游 API 地址。
- 默认 `http://api` 只是占位，部署必须覆盖为实际内部地址。