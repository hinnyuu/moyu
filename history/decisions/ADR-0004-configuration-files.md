# ADR-0004：配置目录多文件化

- 状态：已接受（v0.0.1 架构草稿）
- 日期：2026-11-06

## 背景

需要让 WebUI 管理配置、持久化到 `/config`、缺失自动补默认；同时模块很多，单一配置文件可能成为耦合点。

## 决策

- 使用多文件配置目录：
  - `moyu.yaml` 全局；
  - `modules/<module>.yaml` 每模块一份；
  - `secrets/` 独立敏感文件；
  - `state/last-known-good/` 与备份。
- YAML 1.2 + 严格 schema；拒绝未知字段；禁止 YAML anchor/merge。
- 一个中央 `config` 模块负责加载、校验、合并默认、原子写入、迁移、last-known-good。
- WebUI 聚合展示，按模块分页；运行配置可编辑；部署配置只读/生成部署片段。
- 缺失目录/文件自动补默认；配置损坏优先 last-known-good，没有则失败或只读恢复。
- 端口不写死，来自配置；host/bridge 模式差异在 wiki/UI 中说明。

## 理由

- 与模块 docs/history/wiki 对齐。
- secret 权限隔离。
- 单独校验/备份/回滚。
- 减少多 agent 并发写冲突。
- WebUI 仍然可以用一个界面展示。

## 代价

- 加载/校验/迁移代码更多。
- 需要 schema 管理和跨文件校验。
- 用户手工编辑时需要理解目录结构。

## 替代方案

- 单一 `config.yaml`：初期简单，长期耦合、冲突、secret 混杂。
- 环境变量为主：难以审计/回滚，WebUI 体验差。
- 数据库存配置：迁移/备份复杂，不利于 GitOps/文件挂载。