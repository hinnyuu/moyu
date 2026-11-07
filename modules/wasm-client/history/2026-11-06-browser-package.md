---
date: 2026-11-06
module: wasm-client
commit: (included in this commit)
---

# 浏览器产物构建

## 改动

- 镜像 wasm 阶段使用 wasm-pack 输出 web 目标包。
- 新增本地构建脚本说明。
- Web 动态加载生成物。

## 影响

- 浏览器包由镜像/本地脚本生成，不在仓库提交。
