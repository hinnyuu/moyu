# preview 模块文档

状态：v0.0.1 阶段 2 实现（Pillow + ffmpeg + OpenImageIO，图片/视频/EXR 预览）。

## 职责

媒体探测、图片缩略图/代理、缓存与资源限制。

默认服务端处理；缓存键=资产 sha256+profile；独立容器可限制 CPU/内存/超时；API 只返回预览地址。

图片走 Pillow；视频走 ffmpeg（poster、MP4 代理、HLS）；EXR 走 oiiotool。工具不可用时在 `probe` 返回 `supported: false`，`generate` 返回 `preview_unsupported`。

## 非职责

不打包 ZIP、不改元数据、不直接对公网；只提供 Pod 内部 HTTP 服务。

## 依赖

contracts, storage

## 接口

Python 包位于 `src/moyu_preview/`：

- `PreviewProvider(storage, cache_dir=None, profiles=None, concurrency=2, max_memory_bytes=256MiB, timeout_seconds=60)`
  - `probe(asset_id) -> dict`
  - `generate(asset_id, profile) -> PreviewArtifact`
  - `preview_path(asset_id, profile) -> Path`
  - `delete(asset_id)`
- `PreviewArtifact`：asset_id、profile、path、width、height、format、bytes、cached。
- `PreviewError`：`code` / `message` / `details`。
- `moyu_preview/service.py`：内部 HTTP 服务
  - `GET /healthz`（工具可用性）
  - `GET /probe/{asset_id}`
  - `GET /preview/{asset_id}/{profile}`
  - `GET /preview/{asset_id}/{profile}/{filename}`（HLS 分片/播放列表）
  - `POST /purge/{asset_id}`

内置 profile：

```text
thumb: maxWidth=256, maxHeight=256, format=webp, quality=80
view:  maxWidth=1920, maxHeight=1920, format=jpeg, quality=85
proxy: maxWidth=1280, maxHeight=720, format=mp4, quality=23
```

视频请求 `thumb`/`view` 生成首帧图片；`proxy` 生成 MP4 代理；`hls` 生成 `index.m3u8` 与 TS 分片。

`generate` 也接受自定义 profile 映射。

## 缓存

```text
<preview cache>/<asset-id>/<sha256(asset.sha256 + profile)>/preview.<format>
```

同一资产同一 profile 命中缓存直接返回 `cached: true`，不重新解码。

## 资源限制

- 按 `width * height * 4` 估算解码内存，超过 `max_memory_bytes` 返回 `preview_too_large`。
- 并发由 `threading.BoundedSemaphore` 限制；拿不到槽位返回 `preview_busy`。
- 生成后检查耗时；超时删除输出并返回 `preview_timeout`（Pillow 解码本身不可中断，属于事后检查）。

## 失败模式

资产不存在、格式不支持、解码失败、内存超限、队列忙、超时、磁盘写失败。

## 配置

- `preview.cacheDir`：缓存根目录；
- `preview.serviceUrl`：API 调用预览服务的内部地址；为空时 API 在进程内调用 provider；
- `preview.profiles`：额外/覆盖 profile。
- HLS 播放列表经 API `/api/v1/previews/{id}/hls/index.m3u8` 访问，分片同目录。

## 测试

`tests/test_preview.py` 覆盖：

- 图片 probe（尺寸/格式）；
- thumb 生成、尺寸上限、WEBP 输出、缓存命中不重写；
- view JPEG、自定义 profile、非法 profile；
- 内存上限；
- 视频不支持时 probe/generate 的错误；
- 删除缓存与资产不存在。

运行：

```bash
python3 -m unittest discover -s modules/preview/tests -v
```

## 替换点

ffmpeg / libvips / OpenImageIO provider 可替换 Pillow；接口与缓存键语义不变。视频 poster/MP4/HLS 在启用 ffmpeg 后补充。