# 测试策略（v0.0.1）

## 1. 测试层级

| 层级 | 目的 | 例子 |
| --- | --- | --- |
| 单元测试 | 模块内部逻辑 | 时间换算、DOS 取整、配置校验 |
| 契约/conformance | 可替换实现语义一致 | archive writer、metadata adapter、gateway |
| 集成测试 | 模块组装 | pipeline → metadata → zip → verify |
| 服务测试 | API/worker/storage | 上传、任务、下载、取消、恢复 |
| 部署测试 | Podman pod | 端口、卷、证书、双栈、资源限制 |
| E2E | 浏览器 + 服务 | 上传、打包、预览、下载 |
| 文档门禁 | docs/history/wiki 完整 | agent-gate |

## 2. 媒体测试集

必须覆盖：

- EXR / Multi-Layer EXR
- PNG（tEXt、eXIf、zTXt、iTXt）
- JPEG（COM、EXIF、XMP、APP13）
- TIFF（EXIF、XMP、Photoshop IRB）
- WebP（EXIF、XMP）
- AVIF（Exif、XMP）
- MP4 / MOV（`©day`、非零 `mvhd/tkhd/mdhd`）
- MKV（DATE 标签、DateUTC）

每个格式测试：

- 元数据字段被改写；
- 像素/媒体流字节不变（补丁区间外完全一致）；
- 图片能被 Pillow 解码；
- PNG CRC 合法；
- MP4/MOV/MKV 容器结构不变；
- 严格模式能拒绝无法确认的字段。

## 3. 契约测试

- `archive-zip`：条目名、DOS 时间、extra field、CRC、ZIP64、流式大小。
- `media-metadata`：detect/inspect/plan/apply；materialize 模式。
- `gateway`：TLS、证书热重载、双栈、流式上传、SSE。
- `config`：schema、默认值、迁移、last-known-good、原子写入。
- `uploads`：tus 偏移、断点、完成、清理。
- `preview`：输出格式、缓存键、资源限制。

## 4. 部署测试

- 单镜像，多容器，单 Podman pod。
- external Caddy 模式：无 gateway 容器。
- standalone 模式：gateway + 证书目录。
- 端口自定义；host/bridge 两种 profile。
- IPv4/IPv6 分别 `curl`。
- 证书 A→B 热重载，无重启。
- token 生成/轮换/撤销。
- 资源限制（CPU/内存/PID）。
- 卷权限、SELinux、rootless Podman。

## 5. 大文件与批量

- 单文件 >4GiB（ZIP64）。
- 多文件 >65535 条目（ZIP64 EOCD）。
- 断点续传：断网、刷新页面、进程重启、服务重启。
- 批量上传并发限制。
- 磁盘配额、清理、孤儿会话。

## 6. CI

当前已接入：

- Python 单元测试与进程级 E2E：`python` workflow 遍历 `modules/*/tests`，然后运行 `process_e2e.py`。
- Rust fmt/check/clippy/test/wasm target：`rust` workflow。
- Web typecheck/Vitest/build/Playwright mock E2E：`web` workflow。
- Podman 单镜像构建与五容器 smoke：`podman` workflow。
- 发布：`v*` 标签触发 `release` workflow（GHCR + SBOM + Trivy）。
- `agent-gate` 按 commit 检查。

尚未接入：

- Rust `cargo deny` / `cargo audit`。
- 真实后端联动的 Playwright、明暗主题截图基线与对比度自动检查。
- >4GiB 单文件、服务重启续传等大文件/故障注入测试；>65535 条目已覆盖。
- aarch64 镜像构建与 smoke。

## 7. Agent-gate

- 单元测试：`python3 -m unittest discover -s modules/agent-gate/tests -v`
- 按 commit 检查：`python3 modules/agent-gate/src/agent_gate.py check --base origin/main`
- 检查内容：根 history、模块 history、docs/wiki impact、module.yaml、相对链接、docs history 语气。
- agent-gate 不替代代码测试。

## 8. 不可接受的完成标准

- 只有编译通过，没有行为测试。
- 只测 happy path，不测失败/降级。
- 改了契约但没更新 docs/conformance。
- 改了模块但没有 history/wiki。
- 媒体测试只看“能打开”，不检查流/像素不变。
