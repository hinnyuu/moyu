---
date: 2026-11-06
module: gateway
commit: (included in this commit)
---

# gateway 阶段 2 最小实现

## 改动

- 实现配置解析、证书存储、TLS 反代、管理 API、轮询与 SIGHUP 重载。
- 下游 h2/h1，上游 HTTP/1.1；流式转发，去除 hop-by-hop 头。
- 管理 API 使用文件 token，支持逐请求读取以配合轮换。
- 新增 5 个单元测试。

## 影响

- standalone TLS 入口可用；`enabled: false` 时不监听。
- `watch` 未实现；当前依赖轮询与管理 API。
- 运行时已验证代理、证书轮换与 IPv4/IPv6 双栈。