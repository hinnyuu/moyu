# deploy

Podman/Quadlet、单镜像多容器 pod、卷、端口、证书挂载、镜像构建和运维说明。

- 当前状态：v0.0.1 阶段 2 最小实现（gateway/api/worker）。
- 依赖：全部模块的运维事实
- 接口：Podman pod/Quadlet；镜像构建
- 实现：`bin/`、`container/`、`quadlet/`
- 测试：见 docs 的“测试”

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。