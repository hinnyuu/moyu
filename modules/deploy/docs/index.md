# deploy 模块文档

状态：v0.0.1 阶段 2 实现（单镜像，gateway/api/worker/preview/tusd）。

## 职责

Podman/Quadlet、单镜像多容器 pod、卷、端口、证书挂载、镜像构建和运维说明。

一个镜像、一个 pod、多容器；external Caddy 与 standalone 两种 profile；不使用 Docker Compose；host/bridge 端口说明；资源限制；升级/回滚。

## 非职责

不包含业务代码；不直接控制 Caddy；不管理用户配置。

## 依赖

全部模块的运维事实

## 实现

```text
modules/deploy/
├─ bin/moyu                  # 角色分发入口
├─ container/Containerfile   # 单镜像构建
└─ quadlet/
   ├─ moyu.pod
   ├─ api.container
   ├─ worker.container
   ├─ gateway.container
   └─ deploy.env.example
```

镜像：

- Web 构建阶段：Node 编译 `modules/web/app`；
- Gateway 构建阶段：Rust 编译 `moyu-gateway`；
- WASM 构建阶段：`wasm-pack` 编译 `moyu-wasm-client` 到 Web 静态目录；
- 运行阶段：Python 3.12 + FastAPI/uvicorn/PyYAML/jsonschema/Pillow，包含全部模块源码、Web 静态产物和 gateway 二进制；
- 入口：`moyu <gateway|api|worker>`。

## 容器与端口

当前 pod 包含：

| 容器 | 入口 | 端口 | 卷 |
| --- | --- | --- | --- |
| gateway | `moyu gateway` | `${MOYU_GATEWAY_PORT}`，host 发布 `${MOYU_PUBLIC_PORT}` | `/config` 只读、`/certs` 只读、`/run/secrets` 只读 |
| api | `moyu api` | `${MOYU_API_PORT}`（pod 内） | `/config` 读写、`/data`、`/run/secrets` 只读 |
| worker | `moyu worker` | 无 | `/config` 只读、`/data` |
| preview | `moyu preview` | `${MOYU_PREVIEW_PORT}`（pod 内） | `/config` 只读、`/data` |
| tusd | `moyu tusd` | `${MOYU_TUSD_PORT}`（pod 内） | `/data` |

所有端口和路径来自 `deploy.env` / systemd 环境，不在单元文件中写死。

## 两种模式

### 外部 Caddy

不启动 `gateway.container`，不发布 `${MOYU_PUBLIC_PORT}`；Caddy 反向代理到 Pod 内的 api 端口。

### Standalone TLS

启动 `gateway.container`，发布 `${MOYU_PUBLIC_PORT}:${MOYU_GATEWAY_PORT}`；证书挂载到 `/certs`；管理 API 保持 Pod 内回环。

## 配置要求

- `api.webRoot` 使用镜像默认 `/app/web`（镜像内符号链接到 `/opt/moyu/web`）。
- `storage.dataRoot` 使用 `/data`。
- `preview.cacheDir` 使用 `/data/preview`。
- `gateway.upstream.url` 必须指向 Pod 内 API，例如 `http://api:<api-port>`。
- secret：`/run/secrets/bootstrap_token`、`/config/secrets/session-state.json`、`/config/secrets/session.secret`、`/config/secrets/gateway_reload_token`；tusd hook token 由部署环境变量提供。

## 资源与安全

- `DropCapability=ALL`、`NoNewPrivileges=true`；
- gateway 只读根文件系统 + `/tmp` tmpfs；
- worker/api 使用非 root 用户 `moyu`（UID 1000）；
- api/worker 不发布公网端口；
- 证书目录只读挂载。

## 进程级 E2E

无需 Podman，直接启动 api/worker 子进程，覆盖登录、上传、创建任务、worker 打包、下载与 ZIP/manifest 校验：

```bash
python3 modules/deploy/scripts/process_e2e.py
```

当前沙箱结果：PASS（任务成功，ZIP 1 个条目，manifest sha256 匹配，源资产未被修改）。这条流程也已接入 `python` CI。

## Podman smoke

`.github/workflows/podman.yml` 在 amd64 runner 上安装 Podman，构建单镜像并运行 `modules/deploy/scripts/podman_smoke.sh`：

- 启动 api/worker/preview/tusd/gateway 五容器 pod；
- 验证 pod 网络、TLS gateway、配置/数据/secret 挂载；
- 通过 gateway 完成会话登录；
- 验证 worker/preview/tusd 容器存活。

## 当前限制

- 本沙箱没有 Podman，容器不能本地运行；镜像与 pod 由 amd64 CI 验证。

- 未实现 GHCR 发布 workflow、SBOM/漏洞扫描、升级/回滚脚本。

## 发布

打 `v*` 标签触发 `.github/workflows/release.yml`：

1. 构建单镜像；
2. 推送 GHCR：`:<tag>`、`:sha-<12位>`、`:latest`；
3. Syft 生成 SPDX SBOM；
4. Trivy 生成表格与 SARIF 报告；
5. SBOM 与扫描报告附加到 GitHub Release。

`release` workflow 当前只构建 amd64；`podman-arm64` workflow 在 arm64 runner 上单独验证 arm64 镜像与五容器 smoke。未实现镜像签名。

## 失败模式

端口冲突、卷权限、SELinux、IPv6、证书错误、镜像升级、缺少 secret、上游地址错误。

## 测试

当前可验证的部分：

- `Containerfile` 语法与构建阶段人工审阅；
- 角色入口脚本语法检查（`sh -n`）；
- Quadlet 单元文件与 `deploy.env.example` 占位符一致性；
- 各模块自身测试。

待有 Podman 的环境：

- 构建单镜像；
- `podman play kube` 或 Quadlet 启动 pod；
- 端口/IPv6/TLS 冒烟；
- 升级、回滚、资源限制。

## 替换点

Quadlet ↔ `podman play kube`；部署方式可替换。镜像角色入口保持 `moyu <role>`。