# 项目文档

`docs/` 只记录**当前真实状态**，不记录历史流水账。历史在 `history/`，人类教程在 `wiki/`，模块细节在 `modules/<模块>/docs/`。

## 阅读顺序

1. `architecture/overview.md`：整体架构、范围和边界。
2. `architecture/runtime-topology.md`：镜像、容器、Podman pod、端口、证书。
3. `architecture/modules.md`：模块清单、依赖方向、接口和替换点。
4. `contracts/`：跨模块契约、配置、管理 API、任务模型。
5. `development/`：agent 工作流、风格、Rust workspace、测试。
6. `operations/`：部署模式、数据与备份。

## 文档规则

- 只用现在时描述当前设计。
- 不写“本次修改”“以前是”“迁移记录”；这些去 `history/`。
- 接口、配置、数据模型必须和 `contracts/` 对得上。
- 模块级实现细节写在模块自己的 `docs/`，根级文档只做总览和跨模块事实。
- 关键术语第一次出现时用通俗中文解释，变量名/协议名保留英文。
- 文档必须人类可读；不要只写 agent 才能看懂的压缩语句。

## 索引

- [架构总览](architecture/overview.md)
- [运行时拓扑](architecture/runtime-topology.md)
- [模块清单](architecture/modules.md)
- [契约索引](contracts/README.md)
- [配置契约](contracts/config.md)
- [网关管理 API](contracts/gateway-admin-api.md)
- [模块接口](contracts/module-interfaces.md)
- [Agent Playbook](development/agent-playbook.md)
- [文档风格](development/style-guide.md)
- [Rust workspace](development/rust-workspace.md)
- [测试策略](development/testing.md)
- [部署模式](operations/deployment-modes.md)