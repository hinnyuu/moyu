---
date: 2026-11-06
module: web
commit: (included in this commit)
---

# web 阶段 2 最小实现

## 改动

- 新增 React + Vite + TypeScript 应用：登录、任务、上传、配置四个视图。
- 主题系统：system/light/dark、localStorage、首屏内联脚本、语义 token。
- API 客户端：同源请求、CSRF、统一错误、401 回登录。
- 新增 typecheck/build 脚本与 web workflow。

## 影响

- 静态产物由 API 同源挂载。
- Playwright E2E 与视觉回归待补。

## 已知限制

- 上传分片大小固定 8MiB（与 API 默认 chunkSize 一致），后续可从配置读取。
- 无批量队列与断点恢复 UI。