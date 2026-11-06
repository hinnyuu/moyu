# web 模块文档

状态：v0.0.1 阶段 2 最小实现（React + Vite + TypeScript）。

## 职责

React + Vite + TypeScript 静态 SPA：上传队列、任务、预览、配置、管理。

静态构建，无 SSR；同源 `/api`；批量队列、断点续传、预览、配置表单；WASM 可选懒加载。

## 非职责

不直接访问数据库/文件系统、不承担默认媒体处理。

## 依赖

contracts 生成的客户端（当前为手写 `src/api.ts`）

## 结构

```text
app/
├─ index.html          # 首屏主题脚本，避免亮色闪烁
├─ src/
│  ├─ main.tsx
│  ├─ App.tsx          # 会话、导航、主题
│  ├─ api.ts           # fetch 客户端、CSRF、错误模型
│  ├─ theme.ts         # system/light/dark 解析与持久化
│  ├─ styles.css       # design tokens + 组件样式
│  └─ pages/
│     ├─ Login.tsx     # bootstrap token / 密码登录
│     ├─ Jobs.tsx      # 任务列表、进度、取消
│     ├─ Upload.tsx    # 分片上传、预览、创建任务
│     └─ Settings.tsx  # 配置 JSON 编辑与 revision
├─ package.json
└─ vite.config.ts
```

构建输出 `dist/`，由 API 的 `api.webRoot` 挂载。

## 会话与 CSRF

- 登录调用 `POST /api/v1/auth/session`，cookie 由浏览器保存；
- 登录后 `GET /api/v1/auth/session` 取得 CSRF token，保存在内存；
- 所有写操作带 `X-CSRF-Token`；
- 收到 401 时广播 `moyu:unauthorized`，App 回到登录页。

## 主题与可访问性

- 支持 `system`、`light`、`dark`；默认 `system`。
- 选择写入 `localStorage.moyu-theme`。
- `index.html` 内联脚本在 React 加载前设置 `data-theme`，避免首屏亮色闪烁。
- 颜色全部走 `:root` / `:root[data-theme="dark"]` 语义 token，不在组件里散落硬编码颜色。
- 焦点使用 `:focus-visible` 描边；正文与背景对比度按 WCAG AA 设计。
- 媒体预览使用中性棋盘格背景，不随主题反相。

## 页面

- 登录：未初始化时显示 bootstrap token + 设置密码；已初始化时只显示密码。
- 任务：每 5 秒轮询，显示状态/进度/错误，可取消未完成任务。
- 上传：分片 8MiB，显示进度；完成后显示预览与下载；可创建打包任务。
- 配置：按模块编辑 JSON，保存时带 revision；显示 LKG 降级警告。

## 配置

- `VITE_API_PROXY`：开发时把 `/api` 代理到 API 地址；不设置则不代理。
- 生产由同源 API 挂载 `dist/`，无需代理。

## 失败模式

401 会话过期、403 CSRF、413 请求过大、上传偏移冲突、预览不支持、配置 schema/revision 错误、网络中断。

错误统一显示 `code: message (details)`。

## 测试与构建

```bash
cd modules/web/app
npm ci
npm run typecheck
npm run build
```

已验证：

- `npm run typecheck` 通过；
- `npm run build` 通过（35 modules，dist 生成）；
- 构建产物由 API 静态挂载后可访问（首页、JS、CSS 均为 200）。

尚未完成：

- Playwright 浏览器 E2E（当前沙箱 Chromium 下载受限）；
- 亮/暗主题视觉回归截图基线；
- 组件单测与批量队列。

## 替换点

React 可替换为 Vue/Svelte；只依赖 OpenAPI。主题 token 与页面结构可独立替换。