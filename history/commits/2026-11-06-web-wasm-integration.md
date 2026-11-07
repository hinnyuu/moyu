---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
  - wasm-client
  - deploy
docs_impact: true
wiki_impact: false
wiki_reason: WASM 为可选高级入口，普通上传流程未变化
breaking: false
tests: npm run typecheck; npm test; npm run build; bash -n modules/web/app/scripts/build-wasm.sh; agent-gate --staged
---

# Web WASM 接入与镜像产物

## 背景

发布前审计要求 WASM 可选路径接入 Web；此前只有 Rust 核心与绑定，未产出浏览器包。

## 改动

- Web：
  - 新增 `wasm.ts` 懒加载 `/wasm/moyu_wasm_client.js`；
  - 上传页增加“客户端 ZIP（仅 DOS）”入口，不可用时自动隐藏；
  - i64 参数使用 BigInt；生成 Blob 下载。
- 构建：
  - Containerfile 新增 wasm 阶段，使用 `wasm-pack --target web` 输出到 `/opt/moyu/web/wasm`；
  - 新增本地 `scripts/build-wasm.sh`，输出 `public/wasm/`（gitignore）。
- docs：Web/wasm-client/deploy/README 更新；README 待补清单移除 WASM。

## 影响

- WASM 完全可选：加载失败不影响服务端上传/打包。
- 客户端 ZIP 只写 DOS mtime，不修内部元数据。
- wasm-pack 由镜像构建时安装，版本未固定。

## 验证

- `npm run typecheck`：通过。
- `npm test`：4 passed。
- `npm run build`：通过。
- 本地未安装 wasm-pack，未生成实际 wasm 产物；待 Podman CI 构建确认。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
