# config 模块文档

状态：v0.0.1 阶段 2 最小实现（Python）。

## 职责

配置目录加载、schema 校验、默认值、原子写入、迁移、last-known-good 和变更审计。

读取 `/config` 多文件配置；模块拥有自己的 schema；缺失自动补默认；非法时优先 last-known-good；写入用临时文件 + fsync + rename；WebUI 走 API，不直接读文件。部署配置与运行配置分离，WebUI 不控制 Podman。

## 非职责

不直接执行 Podman、不管理业务数据、不实现 UI、不写 secret 文件。

## 依赖

contracts

## 接口

Python 包位于 `src/moyu_config/`：

- `ConfigProvider(config_dir, schemas_dir=None, read_only=False)`
  - `load() -> EffectiveConfig`
  - `validate(name, data) -> dict`
  - `write(name, patch, revision=None) -> WriteResult`
  - `last_known_good(name) -> dict`
  - `audit(limit=100) -> list`
- `EffectiveConfig`：`global_config`、`modules`、`revisions`、`degraded`、`get(name)`、`to_dict()`。
- `WriteResult`：`name`、`revision`、`data`、`backup`。
- `ConfigError`：`code`、`message`、`details`、`to_dict()`。

`read_only=True` 时不创建目录/文件、不写 LKG、`write` 抛 `read_only`；适合 worker 等只读消费者。

配置名：`global`（`moyu.yaml`）、`gateway`、`api`、`worker`、`preview`、`storage`、`uploads`（`modules/<name>.yaml`）。

schema 位于 `schemas/*.schema.json`；默认值位于 `src/moyu_config/defaults.py`。

## 加载与写入语义

加载：

1. 创建 `config/`、`config/modules/`、`config/state/{last-known-good,backups}/`；
2. 缺失文件写入内置默认值并校验；
3. 已存在文件按 YAML 1.2 解析、禁止 anchor/alias/merge key、按 JSON Schema 严格校验；
4. `schemaVersion` 低于当前版本时执行已注册迁移：先备份到 `state/backups/`，逐版本应用，校验后原子写回；
5. 非法时读取 `state/last-known-good/`；没有 LKG 则抛 `ConfigError`，不静默覆盖用户配置；
6. 成功加载的每个文件写入 LKG。

写入：

1. 读取当前文件并校验，比较 `revision`（文件 sha256）；
2. 深合并 patch，`null` 表示删除字段；
3. 校验通过后先备份到 `state/backups/`，再原子替换；
4. 新内容同步到 LKG；
5. 写入 `state/audit.db` 的 `config_audit` 表（actor、module、action、revision、result、details）；
6. 校验失败或 revision 冲突时不改文件。

## 默认值

默认值是运行配置的起点，不是固定部署事实。端口、路径、证书位置都在默认文件中给出可编辑示例值；gateway 默认关闭，由部署方式决定是否启用。`gateway.upstream.url` 默认 `http://api` 只是占位，部署必须按实际 API 内部地址覆盖。

## 失败模式

- `schema_invalid`：字段类型/范围/未知字段不合法；
- `yaml_invalid` / `yaml_alias`：YAML 解析失败或使用 anchor/alias；
- `revision_conflict`：并发写覆盖；
- `lkg_missing`：配置非法且没有可用 LKG；
- `config_write_failed` / `backup_failed`：磁盘或权限问题；
- `schema_missing` / `schema_invalid`：schema 文件缺失或不是合法 JSON Schema；
- `schema_newer`：配置版本高于当前代码支持；
- `migration_missing`：缺少逐版本迁移；
- `migration_required`：只读模式遇到待迁移配置；
- `audit_failed`：审计库写入失败。

## 测试

`tests/test_config.py` 覆盖：

- 首次加载创建默认文件与 LKG；
- 未知字段触发 LKG 回退；
- 无 LKG 时非法配置启动失败；
- YAML alias 拒绝；
- 写入、revision 冲突、schema 拒绝、备份文件；
- 深合并与 `null` 删除；
- secret 文件不被触碰；
- 默认值全部通过 schema；
- 迁移 1→2、备份、审计 `migrate`；缺少迁移、只读待迁移、schema 过新；
- 写入审计 `write`。

运行：

```bash
python3 -m unittest discover -s modules/config/tests -v
```

## 替换点

格式可换 TOML/JSON，存储可换，但必须保持：多文件、严格 schema、原子写、revision、LKG、secret 分离。