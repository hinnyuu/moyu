# 项目 Wiki

`wiki/` 面向人类读者，解释“是什么、为什么、怎么做、出问题怎么办”。它不记录变更流水账；历史在 `history/`，当前事实在 `docs/`。

## 适合放在这里

- 入门和概念解释；
- 分步骤操作指南；
- 常见错误和排错；
- 部署/运维教程；
- 面向非项目维护者的说明。

## 不适合放在这里

- 提交记录、版本变更；
- 完整接口规范（放 docs/contracts）；
- 临时草稿、TODO 流水账。

## 索引

- [入门](getting-started.md)
- [概念：媒体时间与 ZIP](concepts/media-time.md)
- [概念：镜像、容器与 Podman pod](concepts/image-container-pod.md)
- [操作：Podman 单 Pod 多容器](operations/podman-single-pod.md)
- [操作：HTTPS、端口与证书](operations/https-ports-certificates.md)
- [操作：配置与 WebUI](operations/configuration.md)
- [操作：备份与恢复](operations/backup-restore.md)
- [开发：模块维护流程](development/module-maintenance.md)
- [开发：WebUI 主题与暗色模式](development/webui-style.md)