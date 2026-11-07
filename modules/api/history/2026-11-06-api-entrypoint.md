---
date: 2026-11-06
module: api
commit: (included in this commit)
---

# 容器入口

## 改动

- 新增 `src/moyu_api/__main__.py`：读取 `MOYU_CONFIG_DIR`、storage 配置、认证文件与 `MOYU_API_LISTEN`，启动 uvicorn。

## 影响

- 容器可用 `moyu api` 或 `python -m moyu_api` 启动。
- 端口与 secret 路径来自部署环境，不写死在代码里。
- 认证 cookie 的 `Secure` 由 `MOYU_COOKIE_SECURE=1` 控制。