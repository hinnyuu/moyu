# 发布检查清单（v0.0.1）

发布前逐项确认；任何一项不满足都不打标签。

## 1. 代码与测试

- [ ] `agent-gate`、`python`、`rust`、`web`、`podman` 五个 workflow 全绿。
- [ ] `python` workflow 的进程级 E2E 为 PASS。
- [ ] `podman` workflow 构建单镜像并启动 gateway/api/worker/preview/tusd 五容器 pod。
- [ ] `web` workflow 的 typecheck、Vitest、build 通过。
- [ ] `rust` workflow 的 fmt/check/clippy/test/wasm target 通过。
- [ ] 本地 `agent-gate check --base origin/main` 通过。

## 2. 文档与契约

- [ ] 根 README、AGENTS、docs、wiki 与代码一致。
- [ ] 每个模块 README/docs/wiki 状态与实现一致。
- [ ] `docs/contracts/` 与 OpenAPI/JSON Schema 一致。
- [ ] 所有 docs/wiki 相对链接有效。
- [ ] 没有把 history 流水账写进 docs/wiki。

## 3. 数据与配置

- [ ] `schemaVersion` 迁移路径有测试；迁移前备份生效。
- [ ] `state/last-known-good` 与 `state/audit.db` 写入正常。
- [ ] 备份/恢复步骤覆盖 `/config` 与 `/data`。
- [ ] secret 不进入普通 YAML、不进入镜像、不提交仓库。

## 4. 镜像与供应链

- [ ] 单镜像包含 gateway/api/worker/preview/tusd、Web、WASM、ffmpeg、OIIO。
- [ ] 镜像只从已合并的 `main` 构建。
- [ ] `release` workflow 产出 GHCR `:<tag>`、`:sha-<12位>`、`:latest`。
- [ ] SBOM 与 Trivy 报告附加到 Release。
- [ ] 升级/回滚文档可执行。

## 5. 已知未完成项（发布时必须在 Release notes 说明）

- HLS 预览未实现。
- WASM 转码未实现；客户端只生成 STORE ZIP。
- 仅 amd64 镜像；aarch64 未在 CI 构建/验证。
- Playwright 浏览器 E2E、明暗主题截图基线与对比度自动检查未接入。
- `cargo deny` / `cargo audit` 未接入。
- >4GiB ZIP64、>65535 条目、服务重启续传等大文件/故障注入测试未接入。
- 网关 `watch` 文件监听未实现，使用轮询/管理 API。
- 网关证书 serial/not_after 未解析，只提供文件 SHA-256。

## 6. 打标签

- [ ] 版本号确定为 `v0.0.1`。
- [ ] 在 `main` 打 annotated tag 并推送。
- [ ] 等待 `release` workflow 完成。
- [ ] 检查 GHCR 三个 tag、Release 附件、SBOM、Trivy 报告。
- [ ] 按升级文档在测试环境部署一次并回滚一次。
