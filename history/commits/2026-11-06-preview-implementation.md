---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - preview
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/preview/tests -v; agent-gate --staged
---

# preview 阶段 2 最小实现

## 背景

WebUI 和 API 需要资产预览。当前环境只有 Pillow，没有 ffmpeg/OpenImageIO，因此先实现图片探测与缩略图，视频/EXR 明确返回不支持。

## 改动

- 新增 `modules/preview/src/moyu_preview/`：`PreviewProvider`、`PreviewArtifact`、`PreviewError`。
- 实现 probe、thumb/view 内置 profile、自定义 profile、缓存键、内存上限、并发槽位与超时检查。
- 视频与 EXR 返回 `supported: false`，不假装生成。
- 新增 6 个单元测试。
- 更新 preview 的 README、docs、wiki 和 `module.yaml`。

## 影响

- 图片预览可用，缓存按资产 sha256 + profile 隔离。
- 尚不支持视频 poster/MP4/HLS、EXR tone-map、TIFF 多页代理。
- API 尚未接入预览地址。

## 验证

- `python3 -m unittest discover -s modules/preview/tests -v`：6 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。