# api 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

HTTP API、认证、任务/上传接口、Web 静态文件、管理接口聚合。

FastAPI + OpenAPI；会话认证/CSRF；任务、上传、预览、下载、配置、网关管理；同源服务 Web 静态；不包含打包/媒体处理实现，只编排。

## 非职责

不执行打包、不生成预览、不直接控制 Podman。

## 依赖

contracts, pipeline, storage, uploads, preview, config

## 接口

OpenAPI；GatewayAdmin 客户端；Job/Asset/Config API

## 失败模式

认证失败、请求过大、任务不存在、上游超时、配置校验失败。

## 测试

API 契约、认证、错误码、OpenAPI 生成客户端、静态文件、上传/下载。

## 替换点

FastAPI → 其他框架，OpenAPI 契约不变。
