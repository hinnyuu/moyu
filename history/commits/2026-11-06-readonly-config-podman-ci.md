---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - config
  - worker
  - deploy
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/config/tests -v; python3 -m unittest discover -s modules/worker/tests -v; python3 modules/deploy/scripts/process_e2e.py; bash -n modules/deploy/scripts/podman_smoke.sh; agent-gate --staged
---

# 只读配置与 Podman smoke CI

## 背景

worker 的部署约定是 `/config` 只读，但 `ConfigProvider.load()` 会创建目录、补默认并写 last-known-good，只读挂载会启动失败。同时需要真实的 amd64 Podman 验证单镜像与 pod。

## 改动

- `ConfigProvider` 增加 `read_only`：不创建/写入配置、不写 LKG，`write` 抛 `read_only`。
- worker 入口改为只读加载配置。
- 新增 `modules/deploy/scripts/make_smoke_config.py`、`podman_smoke.sh`。
- 新增 `.github/workflows/podman.yml`：安装 Podman、构建单镜像、启动 api/worker/gateway pod、验证 TLS 健康与登录。
- 更新 config/worker/deploy 的 docs/wiki/module.yaml。

## 影响

- worker 可以只读挂载 `/config`。
- Podman 验证从“待环境”变为 amd64 CI 自动执行。
- smoke 不覆盖完整打包链路（由进程级 E2E 覆盖），只验证容器、网络、TLS、挂载与入口。

## 验证

- config 11 tests、worker 6 tests 通过。
- `process_e2e.py`：PASS。
- `podman_smoke.sh` 语法检查通过。
- 待 GitHub `podman` workflow 确认。