---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# tusd 容器

## 改动

- 镜像下载 tusd v2.8.0 二进制（按 TARGETARCH）。
- `moyu tusd` 入口与 `tusd.container`。
- smoke 改为五容器并检查 tusd 存活。
- 环境变量示例增加 tusd 端口/base path/token。

## 影响

- Pod 覆盖 gateway/api/worker/preview/tusd 五容器。
