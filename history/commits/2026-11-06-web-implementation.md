---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
  - agent-gate
docs_impact: true
wiki_impact: true
breaking: false
tests: npm run typecheck; npm run build; agent-gate --staged
---

# web 阶段 2 最小实现

## 背景

API 已提供会话认证、配置、上传、任务和预览接口，需要浏览器界面串起登录、上传、任务与配置。

## 改动

- 新增 `modules/web/app/`：React 19 + Vite 7 + TypeScript。
- 页面：登录（bootstrap/密码）、任务列表与取消、分片上传与预览/创建任务、按模块配置编辑。
- 主题：`system/light/dark`，localStorage 持久化，`index.html` 内联脚本避免首屏闪烁，语义化 design tokens。
- API 客户端：同源 fetch、内存 CSRF、统一错误模型、401 回登录。
- 新增 `web` workflow：`npm ci` + typecheck + build。
- agent-gate 链接检查跳过 `node_modules`/`dist`/`target` 等目录，并增加测试。
- 更新 web 的 README、docs、wiki 和 `module.yaml`；忽略 `node_modules/`、`dist/`、`*.tsbuildinfo`。

## 影响

- 构建产物可由 `api.webRoot` 同源挂载。
- 生产上传仍建议 tusd；前端使用 API 的 tus 兼容分片端点。
- Playwright E2E 因沙箱 Chromium 下载受限未运行；typecheck/build 与静态挂载已验证。
- 批量队列、WASM 懒加载、视觉回归基线尚未实现。

## 验证

- `npm run typecheck` 通过。
- `npm run build` 通过。
- API 挂载 `dist/` 后首页、JS、CSS 均返回 200。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。