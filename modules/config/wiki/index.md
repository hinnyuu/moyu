# config 模块（人类说明）

config 是配置的“总入口”。WebUI 看起来是一个页面，背后是多个模块配置文件、默认值、校验和备份。

## 什么时候会用到

config 是配置的“总入口”。WebUI 看起来是一个页面，背后是多个模块配置文件、默认值、校验和备份。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/`：跨模块契约。

## Phase 0

配置 schema 已按模块拆分。`gateway.schema.json` 里只有端口范围，没有写死端口；WebUI 和部署文件决定实际值。
