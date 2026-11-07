---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
  - web
  - deploy
docs_impact: true
wiki_impact: false
wiki_reason: 视频转码是可选客户端能力，普通上传/打包流程不变
breaking: false
tests: python3 -m unittest discover -s modules/api/tests -v; npm run typecheck; npm test; npm run build; agent-gate --staged
---

# ffmpeg.wasm 视频转码

## 背景

用户要求 WASM 视频/预览转码作为发布前置条件；此前只有 Rust 图片转码。

## 改动

- Web 引入 `@ffmpeg/ffmpeg`、`@ffmpeg/util`、`@ffmpeg/core`。
- `ffmpeg.ts`：
  - 检查 `crossOriginIsolated`；
  - 懒加载 ffmpeg core；
  - 视频缩放转 MP4（libx264，失败回退 mpeg4）；
  - 失败抛错，UI 提示回退服务端。
- 上传页增加“本地视频转码”按钮与视频预览。
- `scripts/copy-ffmpeg.mjs` 在 dev/build 前复制约 31MB core 到 `public/ffmpeg/`（gitignore）。
- API 与 Vite dev 增加 COOP/COEP 响应头。
- Vitest 增加 2 个回退测试；fullstack Playwright 检查 `crossOriginIsolated`。
- 文档/契约/发布说明更新。

## 影响

- 图片转码走 Rust WASM；视频转码走 ffmpeg.wasm。
- 需要跨源隔离；不满足时按钮禁用/提示回退。
- Web 构建产物与镜像体积增加约 31MB。
- 实际视频转码未在本地浏览器验证；待 CI/人工验证。

## 验证

- API 22 tests；Web Vitest 6 tests；typecheck/build 通过，dist/ffmpeg 存在。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
