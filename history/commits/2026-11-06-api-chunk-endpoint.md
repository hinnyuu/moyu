---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
  - contracts
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/api/tests -v; agent-gate --staged
---

# API 增加 tus 兼容分片端点

## 背景

Web 前端需要可用的上传链路。生产环境由 tusd 处理分片，但同源部署和本地开发没有 tusd，API 只能创建会话、无法写入分片。

## 改动

- 新增 `PATCH /api/v1/uploads/{id}`：要求 `Upload-Offset` 头与 `application/offset+octet-stream` 请求体，返回 204 和新偏移量。
- 请求大小中间件跳过上传分片路径，避免 1MiB JSON 限制误伤。
- API 测试改为通过 HTTP 分片上传，再 finish/下载/预览。
- OpenAPI 补充分片端点与 409 偏移冲突。
- 更新 API docs 与 wiki。

## 影响

- 同源/开发模式可以不用 tusd 完成上传；生产仍建议 tusd。
- 分片仍按顺序写入，偏移不一致返回 409。
- 大文件分片没有单独内存上限，后续可改为流式读取。

## 验证

- `python3 -m unittest discover -s modules/api/tests -v`：14 passed。
- OpenAPI YAML 解析通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。