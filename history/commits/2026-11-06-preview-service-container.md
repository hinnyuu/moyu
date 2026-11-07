---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - preview
  - api
  - config
  - deploy
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/preview/tests -v; python3 -m unittest discover -s modules/api/tests -v; python3 -m unittest discover -s modules/config/tests -v; python3 modules/deploy/scripts/process_e2e.py; bash -n modules/deploy/scripts/podman_smoke.sh; agent-gate --staged
---

# preview 独立服务与容器

## 背景

架构要求 preview 独立容器并支持视频/EXR；此前 preview 内置在 api，镜像也没有 ffmpeg/OIIO。

## 改动

- preview：
  - 新增内部 HTTP 服务与 `moyu preview` / `python3 -m moyu_preview` 入口；
  - 新增 ffmpeg/ffprobe 视频 probe、poster、MP4 代理；
  - 新增 oiiotool EXR 预览；
  - 新增 3 个服务测试，现有图片测试保留。
- api：
  - 新增 `PreviewClient`；`preview.serviceUrl` 非空时代理预览服务，否则进程内 provider；
  - 新增 3 个客户端测试。
- config：`preview.serviceUrl` 加入 schema/defaults。
- deploy：
  - 角色入口增加 preview；
  - 镜像安装 ffmpeg/libvips-tools/openimageio-tools；
  - 新增 `preview.container` 与 `MOYU_PREVIEW_PORT`；
  - Podman smoke 启动四容器 pod 并检查 preview 存活。
- docs/wiki：预览、部署、拓扑、入门更新。

## 影响

- preview 可独立限制资源并隔离 ffmpeg/OIIO；
- api 通过内部 HTTP 调用 preview，失败返回 502；
- HLS 尚未实现；tusd 仍未接入。

## 验证

- preview 9 tests、API 21 tests、config 15 tests：通过。
- 进程级 E2E：PASS。
- `podman_smoke.sh` 语法检查通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
