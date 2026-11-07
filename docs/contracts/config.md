# 配置契约（草稿）

## 1. 目标

- 所有**应用运行配置**都可以在 WebUI 修改；
- 配置落盘到持久目录，容器重建后不丢失；
- 目录/文件缺失时自动补默认；
- 配置损坏时可回到 last-known-good；
- 部署拓扑（卷、网络、host 端口映射）不由 WebUI 直接改 Podman；
- 端口、路径、证书不得写死。

## 2. 目录

```text
/config/
├─ moyu.yaml                 # 全局：schemaVersion、时区默认、模块启用
├─ modules/
│  ├─ gateway.yaml
│  ├─ api.yaml
│  ├─ worker.yaml
│  ├─ preview.yaml
│  ├─ storage.yaml
│  └─ uploads.yaml
├─ secrets/                  # 或 /run/secrets
│  └─ gateway_reload_token
└─ state/
   ├─ last-known-good/
   └─ backups/
```

规则：

- 一个模块一个文件，不做一个巨型 `config.yaml`。
- 根文件只放全局项，不重复模块配置。
- Secret 不进普通 YAML。
- `state/` 由 config 模块管理，用户不直接编辑。

## 3. 配置分类

| 分类 | 例子 | WebUI | 生效方式 |
| --- | --- | --- | --- |
| 部署配置 | 镜像 tag、卷、网络模式、host publish、资源限制、Pod 拓扑 | 只读/展示，或生成部署片段 | 重建 pod/container |
| 运行配置 | 时区、元数据策略、保留天数、预览 profile、并发、清理 TTL | 可编辑 | 热生效 / 重启对应容器 |
| Secret | gateway token、管理员初始 token、外部服务密钥 | 生成/轮换/复制一次，不可回显 | 写 secret 文件，立即或重启生效 |
| Bootstrap | 首次管理员、初始存储路径、监听端口 | 首次启动向导 | 启动时生效 |

WebUI 不挂载 Podman socket，不直接执行 `podman` 命令。

## 4. 文件格式

- YAML 1.2。
- 每个文件带 `schemaVersion`。
- 严格 schema 校验，拒绝未知字段。
- 禁止 YAML anchor/merge 等高级特性，避免跨语言解析差异。
- 类型显式：端口是整数，布尔是 true/false，时间字符串带引号。
- 每个模块拥有自己的 schema 和默认值。

示例 `modules/gateway.yaml`：

```yaml
schemaVersion: 1
enabled: true
listen:
  ipv4: "0.0.0.0"
  ipv6: "::"
  port: 8443          # 示例值，不是固定端口
cert:
  certFile: /certs/tls.crt
  keyFile: /certs/tls.key
  reload:
    onStart: true
    pollInterval: 30s
    watch: false
    signal: false
    api:
      enabled: true
      listen: "127.0.0.1:<admin-port>"
      tokenFile: /config/secrets/gateway_reload_token
upstream:
  url: "http://api:<internal-port>"
```

## 5. 优先级

建议：

1. 代码内置默认值；
2. `/config` 文件；
3. 明确的 bootstrap 环境变量（只用于启动前，例如 `MOYU_CONFIG_DIR`、首次管理员 token）；
4. 不再引入第三套冲突来源。

运行配置以文件为唯一事实；环境变量只做 bootstrap/部署级覆盖。WebUI 修改的是文件，不是环境变量。

## 6. 缺失、损坏、迁移

- `/config` 不存在：创建目录和默认文件。
- 模块文件缺失：使用模块默认值，并写回默认文件。
- 配置非法：
  - 优先加载 `state/last-known-good/`；
  - 没有 last-known-good 时，启动失败或进入只读恢复模式；
  - 不静默用默认值覆盖用户配置。
- `schemaVersion` 升级：
  - 启动时按 `schemaVersion` 逐版本迁移；
  - 迁移前备份到 `state/backups/`，迁移后校验并原子写回；
  - 缺少逐版本迁移返回 `migration_missing`；只读模式遇到待迁移返回 `migration_required`；版本高于代码返回 `schema_newer`；
  - 失败则回滚并报告。
- 写入：
  - 临时文件 + fsync + 原子 rename；
  - 单写者 + 文件锁；
  - WebUI 带 revision/ETag，防止并发覆盖；
  - 校验通过后才替换现文件。

## 7. WebUI 行为

- 统一读取 effective config，按模块分页展示。
- 保存前校验；展示变更 diff 和影响等级：
  - 热生效；
  - 重启 api/worker/preview/gateway；
  - 需要重建 pod；
  - 只读部署项。
- 运行配置可编辑；部署配置只读或生成 Quadlet/pod 片段供下载。
- Secret 生成/轮换后只展示一次，可复制；数据库只存 hash。
- 所有修改写 `state/audit.db` 的 `config_audit` 表：时间、actor、模块、动作、前后 revision、结果、详情；不写入项目 `history/`。
- 审计通过 `GET /api/v1/config/audit` 读取。
- 支持一键恢复 last-known-good。

## 8. 端口

- 端口来自配置，不写死。
- host network 模式：gateway 直接绑定 `gateway.listen.port`。
- bridge 模式：`gateway.listen.port` 是容器端口，host 端口由 Quadlet `PublishPort` 决定；WebUI 改端口时提示需要改部署文件并重建 pod。
- external Caddy 模式：公网端口由 Caddy 决定，项目只配置内部监听端口。
- 端口范围 1–65535；<1024 在 rootless Podman 下需要额外能力，UI 要提示。

## 9. 配置与项目 history 的区别

- 项目 `history/` 记录代码、契约、schema 的变化。
- 用户运行时修改配置是**运行数据**，记录在数据库审计表和配置文件备份里，不进入 Git history。
- 配置 schema 变更必须更新 `docs/contracts/config.md` 和项目 history。