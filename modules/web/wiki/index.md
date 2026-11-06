# web 模块（人类说明）

web 是浏览器里的操作界面：登录、上传、看任务、改配置。

## 本地开发

```bash
cd modules/web/app
npm ci
VITE_API_PROXY=http://<api-host>:<api-port> npm run dev
```

Vite 会把 `/api` 代理到 API；生产构建用：

```bash
npm run build
```

## 主题

右上角“主题”按钮在“跟随系统 → 亮色 → 暗色”之间切换，选择会记住。首屏由 `index.html` 的内联脚本在 React 之前应用主题，所以刷新不会先闪一下亮色。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- `wiki/development/webui-style.md`：视觉规范。
- `modules/contracts/openapi/openapi.yaml`：HTTP 契约。