# 契约索引

moyu 采用 **contract-first**：模块之间先对齐契约，再写实现。实现可以替换，契约和 conformance 不能悄悄变化。

## 契约列表

| 契约 | 内容 | 文档 |
| --- | --- | --- |
| 模块接口 | 时间策略、元数据适配器、归档写入、存储、预览、配置、网关管理 | `module-interfaces.md` |
| 配置 | 配置目录、schema、默认值、WebUI、secret、迁移 | `config.md` |
| 网关管理 API | 证书重载、状态、token、暴露面 | `gateway-admin-api.md` |
| HTTP API | 上传、任务、下载、预览、认证 | [`openapi.yaml`](../../modules/contracts/openapi/openapi.yaml) |
| Pack Plan | 目标时间、补丁计划、manifest | `module-interfaces.md` |
| Gateway token | 生成、轮换、撤销、复制一次 | `gateway-admin-api.md` |

## 契约规则

1. 契约用机器可读格式落地：OpenAPI、JSON Schema、明确的 Rust/Python 类型。
2. 契约变更必须更新 `docs/contracts/` 和对应模块 docs。
3. 破坏性契约变更必须有 ADR，记录在 `history/decisions/`。
4. 每个可替换实现都必须通过同一套 conformance 测试。
5. 契约中不写死端口、路径、镜像标签；这些是配置或部署参数。

## 版本

- 项目版本从 `v0.0.1` 开始；实现已存在，但尚未发布标签。
- API 路径带主版本，例如 `/api/v1/...`。
- 内部契约有 `contract_version`；破坏性变更必须升版本并提供迁移说明。
- 配置有 `schemaVersion`，启动时迁移；迁移前备份到 `state/backups/`。

## 机械契约文件

- [OpenAPI](../../modules/contracts/openapi/openapi.yaml)
- [PackPlan Schema](../../modules/contracts/schemas/pack-plan.schema.json)
- [MetadataReport Schema](../../modules/contracts/schemas/metadata-report.schema.json)
- [Job Schema](../../modules/contracts/schemas/job.schema.json)
- [GatewayToken Schema](../../modules/contracts/schemas/gateway-token.schema.json)
- [配置 schema 目录](../../modules/config/schemas/)
