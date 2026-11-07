---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - deploy
docs_impact: false
docs_reason: 仅修正镜像构建中的 tusd 解压路径，部署行为与文档不变
wiki_impact: false
wiki_reason: 操作流程未变化
breaking: false
tests: bash -n modules/deploy/scripts/podman_smoke.sh; agent-gate --staged
---

# 修复 tusd 镜像构建解压路径

## 背景

Podman CI 构建 tusd 阶段失败：`install: cannot stat '/tmp/tusd'`。发布包解压后二进制不在 `/tmp/tusd`，而是位于子目录或使用不同文件名。

## 改动

- 解压后使用 `find` 在 `/tmp` 下定位 `tusd` 或 `tusd_*` 文件（排除 `.tar.gz`）。
- 校验找到路径后再 `install` 到 `/usr/local/bin/tusd`。
- 清理下载包。

## 影响

- 不依赖 tusd 发布包内部目录结构。
- 若发布包没有匹配文件，构建仍会失败，但不会再误装不存在的路径。

## 验证

- 本地网络无法完成发布包下载，未能复现解压目录。
- 待 `podman` workflow 重新构建确认。
