# config 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

配置目录加载、schema 校验、默认值、原子写入、迁移、last-known-good 和变更审计。

读取 `/config` 多文件配置；模块拥有自己的 schema；缺失自动补默认；非法时优先 last-known-good；写入用临时文件 + fsync + rename；WebUI 走 API，不直接读文件。部署配置与运行配置分离，WebUI 不控制 Podman。

## 非职责

不直接执行 Podman、不管理业务数据、不实现 UI。

## 依赖

contracts

## 接口

ConfigProvider：load / validate / write / last_known_good

## 失败模式

schema 不兼容、文件损坏、并发写、secret 权限、迁移失败。

## 测试

schema、默认值、迁移、并发、last-known-good、原子写、secret 权限。

## 替换点

格式可换 TOML/JSON，存储可换，但语义一致。
