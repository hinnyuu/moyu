---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - wasm-client
  - web
docs_impact: true
wiki_impact: false
wiki_reason: 转码是可选客户端能力，普通上传/打包流程不变
breaking: false
tests: cargo test -p moyu-wasm-client; cargo clippy -p moyu-wasm-client --all-targets -- -D warnings; cargo check -p moyu-wasm-client --target wasm32-unknown-unknown; npm run typecheck; npm test; npm run build; agent-gate --staged
---

# WASM 图片转码

## 背景

发布说明把“WASM 转码未实现”列为限制；用户要求补齐后再发布。

## 改动

- wasm-client 增加 `image` crate（png/jpeg）。
- 新增 `transcode_image(data, maxWidth, maxHeight, format, quality)`：
  - PNG/JPEG 解码、Lanczos3 缩放、PNG/JPEG 编码；
  - 64M 像素上限；
  - 错误统一为 `PackError::Transcode`。
- WASM 绑定增加 `transcode(...)`，capabilities 声明转码格式。
- Web 增加 `transcodeImage` 与“本地预览转码”按钮。
- docs/contract/release notes 更新：图片转码已实现，视频转码仍未实现。

## 影响

- 客户端可本地缩放图片预览；视频仍回退服务端。
- wasm 产物增大，构建时间增加。

## 验证

- wasm-client 8 tests 通过。
- clippy 与 wasm32 check 通过。
- Web typecheck/build/Vitest 通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
