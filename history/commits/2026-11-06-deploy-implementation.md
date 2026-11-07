---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - deploy
  - api
  - worker
docs_impact: true
wiki_impact: true
breaking: false
tests: sh -n modules/deploy/bin/moyu; python3 -m unittest discover -s modules/api/tests; python3 -m unittest discover -s modules/worker/tests; agent-gate --staged
---

# deploy 阶段 2 最小实现

## 背景

gateway、api、worker 已可运行，需要单镜像多容器的 Podman 部署骨架和容器入口。

## 改动

- 新增 `modules/deploy/bin/moyu`：`gateway|api|worker` 角色分发。
- 新增 `modules/deploy/container/Containerfile`：Web 构建、Rust gateway 构建、Python 运行时单镜像。
- 新增 `modules/deploy/quadlet/`：pod、api、worker、gateway 单元与 `deploy.env.example`。
- api 增加 `python -m moyu_api` 入口：读取配置目录、storage、认证文件与监听地址。
- worker 增加 `python -m moyu_worker` 入口：启动恢复、循环领取、SIGTERM/SIGINT 停止。
- 新增 `.dockerignore`，排除依赖与构建产物。
- 更新 deploy 的 README/docs/wiki/module.yaml，以及 api/worker 的入口说明。

## 影响

- 单镜像可以按角色启动 gateway/api/worker。
- preview 仍由 api 进程内调用；tusd 尚未入镜像，当前使用 API 分片端点。
- 未实现 GHCR 发布、SBOM/漏洞扫描、升级/回滚脚本。
- 沙箱没有 Podman，镜像与 pod 未实际构建/运行验证。

## 验证

- `sh -n modules/deploy/bin/moyu`：通过。
- API 与 worker 单元测试通过（入口文件不被测试导入）。
- 待有 Podman 的环境执行镜像构建与 pod smoke。