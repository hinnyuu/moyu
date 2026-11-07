---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# deploy 阶段 2 最小实现

## 改动

- 新增角色入口 `bin/moyu`。
- 新增单镜像 `container/Containerfile`：Web、gateway、Python 运行时。
- 新增 Quadlet pod/api/worker/gateway 与环境变量示例。
- 新增 `.dockerignore`。

## 影响

- 支持外部 Caddy 与 standalone TLS 两种 pod 组合。
- 端口与路径全部来自部署环境变量。
- 未包含 preview 独立容器与 tusd；待后续补齐。