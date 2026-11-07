---
date: 2026-11-06
module: api
commit: (included in this commit)
---

# 预览服务客户端

## 改动

- 新增 `PreviewClient` 与错误映射。
- `preview.serviceUrl` 配置后代理内部服务，否则使用进程内 provider。
- 新增 3 个客户端测试。

## 影响

- 部署模式使用独立 preview 容器；测试/开发模式仍可内联。
