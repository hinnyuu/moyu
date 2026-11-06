# deploy 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

Podman/Quadlet、单镜像多容器 pod、卷、端口、证书挂载、GHCR 发布和运维 wiki。

一个镜像、一个 pod、多容器；external Caddy 与 standalone 两种 profile；不使用 Docker Compose；host/bridge 端口说明；资源限制；升级/回滚；GHCR。

## 非职责

不包含业务代码；不直接控制 Caddy；不管理用户配置。

## 依赖

全部模块的运维事实

## 接口

Podman pod/Quadlet；镜像构建/发布

## 失败模式

端口冲突、卷权限、SELinux、IPv6、证书、镜像升级。

## 测试

Podman pod smoke、端口/IPv6、TLS、升级、资源限制。

## 替换点

Quadlet ↔ play kube；部署方式可替换。
