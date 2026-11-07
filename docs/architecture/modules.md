# 模块清单与边界（v0.0.1）

## 1. 模块原则

- 每个模块是**可替换单元**，不是按技术层随意切分的目录。
- 模块只暴露 `contracts` 中的接口；不得直接 import 其他模块内部实现。
- 每个模块拥有：
  ```text
  module.yaml
  README.md
  AGENTS.md
  docs/
  history/
  wiki/
  src/        # 实现
  tests/      # 测试
  ```
- 模块可以独立维护、测试、替换；替换时其他模块只改装配配置。

## 2. 模块列表

| 模块 | 职责 | 依赖 | 主要替换点 |
| --- | --- | --- | --- |
| `contracts` | OpenAPI、JSON Schema、模块接口、生成客户端 | 无 | 契约版本化 |
| `core-time` | 时间策略、DOS/EXIF/QuickTime/Matroska 时间换算、Rust core crate | contracts | 纯逻辑，可独立测试 |
| `media-metadata` | 格式识别、探测、补丁计划、流式改写；每格式一个 adapter | contracts, core-time | 可换 Rust/外部工具 |
| `archive-zip` | ZIP 写入、ZIP64、extra field 校验 | contracts | Python → Rust 实现 |
| `pipeline` | 扫描、时间映射、调用 metadata adapter、打包、manifest、校验 | core-time, media-metadata, archive-zip | 业务编排 |
| `config` | 配置加载、schema 校验、默认值、原子写入、last-known-good | contracts | YAML/TOML、存储后端 |
| `storage` | 上传暂存、资产、任务、输出、预览缓存、配额、清理 | contracts | 本地 FS → NAS/S3 |
| `uploads` | tus 会话、完成钩子、入库 | contracts, storage | tusd → 其他协议 |
| `preview` | 媒体探测、图片/视频/EXR 预览、MP4 代理；HLS 待补 | contracts, storage | ffmpeg/libvips/OpenImageIO |
| `api` | HTTP API、认证、任务/上传接口、Web 静态文件 | contracts, pipeline, storage, uploads, preview, config | FastAPI → 其他 |
| `worker` | 后台打包任务、进度、取消、恢复 | pipeline, storage, config | 单进程 → 队列 |
| `web` | React + Vite + TypeScript 静态 SPA，支持 system/light/dark 主题 | contracts 生成客户端 | 框架可替换 |
| `wasm-client` | 可选浏览器 ZIP；转码待补；Rust WASM | contracts, core-time | 可禁用/替换 |
| `gateway` | Rust TLS、反向代理、证书热重载、双栈、token API | contracts, config | Rust 实现可替换 |
| `deploy` | Podman/Quadlet、卷、端口、GHCR、发布与运维文档 | 全部模块的运维事实 | 部署实现可替换 |
| `agent-gate` | 文档/history/wiki/契约门禁 | 仓库自身 | 工具可替换 |

## 3. 依赖方向

```text
contracts
  ↑
core-time ← media-metadata ← pipeline ← api / worker
  ↑              ↑
archive-zip     config / storage ← uploads / preview
  ↑
web（只依赖 API 客户端）
```

规则：

- 禁止循环依赖。
- `contracts` 不依赖任何业务模块。
- `core-time` 不依赖 I/O、数据库、Web。
- `media-metadata` 不依赖 ZIP、Web、数据库。
- `preview` 不依赖打包 pipeline；它只消费资产。
- `web` 不直接 import 后端代码，只使用手写 fetch 客户端（契约由 OpenAPI 约束）。
- `deploy` 不参与运行时业务逻辑。

## 4. 标准接口

接口文档在 `docs/contracts/module-interfaces.md`：

- `TimePolicy`
- `MetadataAdapter`
- `ArchiveWriter`
- `JobStore`
- `AssetStore`
- `UploadSessionStore`
- `PreviewProvider`
- `ConfigProvider`
- `GatewayAdmin`
- `WasmPackClient`

每个接口都有：

- 输入/输出模型；
- 错误模型；
- 同步/异步语义；
- 版本；
- conformance 测试要求。

## 5. Rust workspace

Rust 只用于：

- `gateway`：原生 TLS/反代；
- `wasm-client`：浏览器 ZIP/预览核心；
- `moyu-core`（core-time）：target-neutral 的时间/DOS/契约类型。

结构：

```text
/Cargo.toml                  # workspace
/modules/gateway/rust/
/modules/wasm-client/rust/
/modules/core-time/rust/     # package: moyu-core
```

- 一个 workspace，三个 crate。
- gateway 和 wasm-client 不互相依赖。
- `moyu-core` 不引入 tokio/hyper/文件系统等原生依赖。
- 每个 crate 的 docs/history/wiki 仍在对应模块目录下。

## 6. 替换与 conformance

替换模块时，必须通过同一套 conformance：

- `archive-zip`：条目名、DOS 时间、无时间 extra、CRC、ZIP64。
- `media-metadata`：每种格式的探测、补丁等价、媒体流不变。
- `gateway`：TLS、证书热重载、双栈、流式转发、管理 API。
- `uploads`：断点续传、偏移、完成、清理。
- `preview`：输出格式、尺寸、缓存键、资源限制。
- `config`：schema、默认值、迁移、原子写入。

没有 conformance 的“替换”不算完成。

## 7. 模块文档模板

每个模块的 `docs/index.md` 至少包含：

1. 职责和非职责；
2. 接口和依赖；
3. 配置项；
4. 数据模型/状态机；
5. 失败模式和降级；
6. 测试方式；
7. 替换点；
8. 安全注意事项。

`history/index.md` 只追加，不覆盖；`wiki/index.md` 面向人类解释，不写流水账。