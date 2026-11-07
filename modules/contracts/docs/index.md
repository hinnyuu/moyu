# contracts 模块文档

状态：契约已建立，随实现持续更新，v0.0.1 前冻结。

## 职责

跨模块接口、OpenAPI、JSON Schema 和生成客户端的唯一事实来源。

本模块只定义契约，不实现业务逻辑。所有跨模块调用、任务模型、配置 schema、网关管理 API 和 WASM 能力声明都以这里为准。实现模块不得私自扩展隐藏参数。

## 非职责

不包含业务实现；不绑定具体语言；不直接访问运行时资源。

## 依赖

无

## 接口

OpenAPI、JSON Schema、模块接口契约

## 失败模式

契约解析失败、版本不兼容、生成客户端失败。

## 测试

OpenAPI/JSON Schema 校验、版本兼容检查、生成客户端编译。

## 替换点

契约本身不替换，只做版本升级；旧版本必须保留迁移说明。

## 机械契约文件

- `openapi/openapi.yaml`：应用 API 草稿。
- `schemas/pack-plan.schema.json`：PackPlan。
- `schemas/metadata-report.schema.json`：元数据报告。
- `schemas/job.schema.json`：任务模型。
- `schemas/gateway-token.schema.json`：网关 token 元数据。
- 当前由 `agent-gate` 做结构和链接检查；完整 schema 校验在后续阶段接入。
