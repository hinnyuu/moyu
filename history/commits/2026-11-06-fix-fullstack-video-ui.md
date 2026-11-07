---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: false
docs_reason: 仅调整视频转码入口展示位置与测试登录，文档能力描述不变
wiki_impact: false
wiki_reason: 用户操作不变
breaking: false
tests: npm run typecheck; npm run build; npx playwright test --list; agent-gate --staged
---

# 修复 fullstack 视频转码入口与测试隔离

## 背景

fullstack 日志：
1. 等待“本地视频转码”按钮超时；
2. 第二个测试等待 `#bootstrap` 超时。

## 原因

- “本地视频转码”按钮放在 `wasmReady` 区块内，但 fullstack 构建没有 Rust WASM 产物（`/wasm/...js` 404），区块不渲染。
- 两个测试共用同一 API：第一个测试已初始化管理员，第二个仍等待 bootstrap 输入框。

## 改动

- 视频转码按钮拆到独立区块，只依赖 `ffmpegSupported()`，不依赖 Rust WASM。
- 两个 fullstack 测试统一使用 `login()` helper，自动识别“初始化”或“已初始化”。

## 影响

- 无 Rust WASM 产物时仍可使用 ffmpeg.wasm 视频转码。
- 测试顺序无关。

## 验证

- typecheck/build 通过；Playwright 用例列表正常。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
