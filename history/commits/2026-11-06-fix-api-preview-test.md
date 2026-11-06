---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
docs_impact: false
docs_reason: 仅修正测试使用临时预览目录，API 行为与文档描述未变化
wiki_impact: false
wiki_reason: 使用流程未变化
breaking: false
tests: python3 -m unittest discover -s modules/api/tests -v; agent-gate --staged
---

# 修复 API 预览测试在 CI 的缓存目录

## 背景

GitHub Actions 的 `python` workflow 在 `test_upload_download_and_preview` 失败：
测试使用默认配置 `preview.cacheDir=/data/preview`，runner 无法创建 `/data`，导致
`PermissionError`。

## 改动

- 测试 setUp 在 `create_app` 之前把 `preview.cacheDir` 写到 storage 的临时 preview 目录。
- 测试仍覆盖配置写入与 revision 语义。

## 影响

- 本地与 CI 都在临时目录生成预览，不依赖 `/data` 权限。
- 生产配置仍由部署决定 `preview.cacheDir`。

## 验证

- `python3 -m unittest discover -s modules/api/tests -v`：14 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
- 待 GitHub `python` workflow 确认。