---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - preview
  - api
  - web
docs_impact: true
wiki_impact: false
wiki_reason: HLS 是高级预览入口，普通上传/打包流程未变化
breaking: false
tests: python3 -m unittest discover -s modules/preview/tests -v; python3 -m unittest discover -s modules/api/tests -v; npm run typecheck; npm run build; npm test; agent-gate --staged
---

# HLS 预览

## 背景

发布清单仍列 HLS 未实现；架构要求视频代理/HLS。

## 改动

- preview：
  - 新增 `hls` profile；
  - ffmpeg 生成 `index.m3u8` + TS 分片；
  - 服务新增 `/preview/{id}/{profile}/{filename}`，按目录安全校验后返回分片/播放列表；
  - 新增 HLS 测试（ffmpeg 可用时）与缺失文件测试。
- api：
  - `PreviewClient.generate_file`；
  - 新增 `/api/v1/previews/{id}/{profile}/{filename}` 代理，含路径校验。
- web：
  - 新增 `HlsPreview` 组件，`hls.js` 动态加载；
  - 上传页选择资产后可打开 HLS 播放器。
- docs：preview/web/README/契约/发布清单更新，移除 HLS 未完成项。

## 影响

- HLS 播放列表通过 API 访问：`/api/v1/previews/{id}/hls/index.m3u8`，分片相对路径。
- 非视频资产请求 HLS 会返回 unsupported；播放器显示错误。
- `hls.js` 按需加载，不进入首屏主包。

## 验证

- preview 11 tests（1 个 HLS 因本机无 ffmpeg 跳过）。
- API 22 tests。
- Web typecheck/build/Vitest 通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
