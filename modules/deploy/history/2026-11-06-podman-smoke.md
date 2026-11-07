---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# Podman smoke

## 改动

- 新增 `scripts/make_smoke_config.py`：生成容器用配置。
- 新增 `scripts/podman_smoke.sh`：构建后可启动 api/worker/gateway pod，验证 TLS、登录与 worker 存活。
- 新增 `.github/workflows/podman.yml`。

## 影响

- 容器编排在 amd64 CI 上获得真实验证。
- 完整打包链路仍由进程级 E2E 覆盖。