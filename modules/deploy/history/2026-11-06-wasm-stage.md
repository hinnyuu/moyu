---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# 镜像增加 WASM 构建阶段

## 改动

- 新增 rust wasm 阶段，输出到 `/opt/moyu/web/wasm`。

## 影响

- 单镜像包含可选 WASM 产物；构建时间增加。
