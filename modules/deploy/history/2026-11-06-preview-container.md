---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# preview 容器与媒体工具

## 改动

- 角色入口增加 preview。
- 镜像安装 ffmpeg/libvips-tools/openimageio-tools。
- 新增 preview.container 与环境变量。
- smoke 启动四容器并检查 preview 存活。

## 影响

- Pod 从三容器变为四容器；tusd 仍待接入。
