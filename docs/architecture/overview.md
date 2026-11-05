# 架构总览（v0.0.1 草稿）

## 1. 范围

moyu 的目标不是“把旧脚本装进容器”，而是以**交付 ZIP 是唯一需要维护的产物**为核心，重新组织：

- 时间策略：把源文件 mtime 的相对关系映射到目标时间。
- 媒体元数据：改写交付文件内部的渲染时间字段。
- 归档：生成只包含 DOS mtime、没有时间类 extra field 的 ZIP。
- 服务：上传、任务、打包、预览、下载。
- 部署：单镜像、单 Podman pod、多容器；Caddy 可选。

## 2. 非目标

- v0.0.1 不做多人协作、多租户、复杂权限模型。
- 不把 Docker Compose 作为部署依赖。
- 不把浏览器 WASM 作为默认媒体处理路径。
- 不在 v0.0.1 实现完整媒体资产管理、版本控制或渲染农场调度。
- 不修改用户本地源文件作为默认行为；源文件时间保持不变。

## 3. 运行形态

### 3.1 一个镜像

只发布一个镜像：

```text
ghcr.io/hinnyuu/moyu:<version>
```

镜像内包含全部角色入口，由 `moyu <role>` 分发：

- `moyu gateway`
- `moyu api`
- `moyu worker`
- `moyu preview`
- `moyu tusd`

### 3.2 一个 Podman pod

不使用 Docker Compose 作为部署依赖。Podman 原生使用：

- `podman pod create` + `podman run --pod`；或
- Quadlet：`.pod` + 多个 `.container` 单元；或
- `podman play kube` 的 Pod YAML。

容器边界：

| 容器 | 职责 | 对外端口 |
| --- | --- | --- |
| `gateway` | TLS、证书热重载、双栈、反向代理；standalone 模式启用 | 可配置 |
| `api` | HTTP API、认证、任务/上传接口、Web 静态文件 | 仅 Pod 内 |
| `worker` | 打包任务执行 | 无 |
| `preview` | 媒体探测、缩略图、代理视频/图片 | 仅 Pod 内 |
| `tusd` | 大文件断点续传 | 仅 Pod 内 |

外部 Caddy 模式省略 `gateway`；Caddy 负责公网端口和 TLS。

### 3.3 单镜像、多容器

- 镜像只构建一次，所有容器共享镜像层。
- 每个容器有独立的进程、可写层、cgroup、日志和重启策略。
- Pod 内共享网络 namespace；gateway 管理 API 可以监听 `127.0.0.1:<admin-port>`，api 通过回环访问。
- 不建议把所有角色塞进一个容器：preview 的崩溃/OOM 不能拖垮 api，gateway 需要独立资源限制。

## 4. 模块与依赖

主要模块：

- `contracts`：OpenAPI、JSON Schema、模块接口。
- `core-time`：时间策略、DOS/EXIF/QuickTime/Matroska 时间转换。
- `media-metadata`：格式识别、探测、补丁计划、流式改写。
- `archive-zip`：ZIP 写入、ZIP64、extra field 校验。
- `pipeline`：打包编排、manifest、验证。
- `config`：配置加载、校验、原子写入、last-known-good。
- `storage`：上传暂存、资产、任务、输出、预览缓存。
- `uploads`：tus 会话、完成钩子。
- `preview`：缩略图、图片代理、视频代理/HLS。
- `api`：HTTP 接口、认证、Web 静态。
- `worker`：后台打包。
- `web`：React + Vite + TypeScript 静态 SPA。
- `wasm-client`：可选浏览器 ZIP/预览转码。
- `gateway`：Rust TLS/反代/证书热重载。
- `deploy`：Podman/Quadlet、卷、端口、GHCR。
- `agent-gate`：文档/history/wiki/契约门禁。

依赖方向：

```text
contracts
  ↑
core-time ← media-metadata ← pipeline ← api / worker
  ↑              ↑
archive-zip     config / storage ← uploads / preview
  ↑
web（只依赖生成的 API 客户端）
```

禁止循环依赖，禁止模块直接 import 对方内部实现。

## 5. 数据流

### 打包

```text
上传/选择文件
  → storage 资产
  → api 创建 job
  → worker 拉取 job
  → core-time 计算目标时间
  → media-metadata 生成补丁/重建流
  → archive-zip 写 ZIP
  → 校验 ZIP 结构 + manifest
  → 输出交付 ZIP
```

### 预览

```text
资产入库
  → preview 探测格式
  → 生成缩略图/图片代理/视频代理/HLS
  → 缓存到 preview 存储
  → api 返回预览地址
```

### 配置

```text
/config 文件
  → config 模块加载/校验/合并默认
  → effective config 快照
  → 各模块按需读取
  → WebUI 通过 api 读写运行配置
```

## 6. 文档、history、wiki

三者物理隔离：

- `docs/`：当前事实。
- `history/`：按时间追加的提交/决策记录。
- `wiki/`：人类可读教程。

每个模块也有自己的 `docs/history/wiki`。根级只做项目级总览和索引，不复制模块正文。

## 7. 关键决策摘要

- 网关用 Rust，与 WASM 共用 Rust workspace；不引入 Go。
- 单镜像、多容器、单 Podman pod；不拆镜像，不使用 Compose。
- `api`、`worker`、`preview`、`tusd` 从第一天分开；`gateway` 在 standalone 模式独立容器。
- 默认服务端媒体处理；WASM 是早期可选路径。
- 端口不写死，使用配置；host/bridge 均可，端口变更需要相应重启或重建。
- 配置多文件、按模块划分，WebUI 统一编辑；部署拓扑不由 WebUI 直接控制 Podman。
- 证书热重载默认轮询 + API；token 由 WebUI 生成/轮换/复制；API 只触发重读挂载文件。

详细决策理由在 `history/decisions/`。