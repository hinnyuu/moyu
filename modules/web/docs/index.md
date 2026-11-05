# web 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

React + Vite + TypeScript 静态 SPA：上传队列、任务、预览、配置、管理。

静态构建，无 SSR；同源 `/api`；TanStack Query/上传状态机；批量队列、断点续传、预览播放、配置表单、token 管理；WASM 可选懒加载。

## 非职责

不直接访问数据库/文件系统、不承担默认媒体处理。

## 依赖

contracts 生成的客户端

## 接口

HTTP API；可选 lazy WASM

## 失败模式

上传中断、API 错误、预览格式不支持、WASM 能力不足。

## 测试

组件/状态机、typecheck、Playwright 上传/预览/配置。

## 替换点

React 可替换为 Vue/Svelte；只依赖 OpenAPI。
