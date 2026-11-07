---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - api
  - uploads
  - deploy
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/api/tests -v; python3 modules/deploy/scripts/process_e2e.py; bash -n modules/deploy/bin/moyu; bash -n modules/deploy/scripts/podman_smoke.sh; agent-gate --staged
---

# tusd 容器与内部完成钩子

## 背景

架构要求 tusd 独立容器；此前只有内嵌分片端点，tusd 未进镜像/pod。

## 改动

- 镜像增加 tusd 二进制构建阶段（下载 v2.8.0 release，按 TARGETARCH 选择）。
- `moyu tusd` 角色读取监听、上传目录、base path、hook URL/token 并启动 tusd。
- API 新增 `POST /api/v1/internal/tusd/hook`：
  - token 校验；
  - `pre-create` 校验大小与配额；
  - `post-finish` 登记资产；
  - 不要求浏览器会话。
- 部署新增 `tusd.container`、环境变量；五容器 pod。
- Podman smoke 启动并检查 tusd 容器。
- 文档更新 uploads/api/deploy/拓扑/wiki。

## 影响

- tusd 只在 Pod 内监听；hook token 由部署环境提供。
- 内嵌分片端点保留，开发/同源部署不依赖 tusd。
- tusd 完成后的文件由 AssetStore 移入资产目录。
- HLS 仍未实现。

## 验证

- API 22 tests：通过。
- 进程级 E2E：PASS。
- 入口与 smoke 脚本语法检查：通过。
- tusd 发布包 URL 返回 200。
- 待 `podman` workflow 构建与 smoke 验证。
