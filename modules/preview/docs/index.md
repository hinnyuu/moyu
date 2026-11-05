# preview 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

媒体探测、图片缩略图/代理、视频 poster/MP4/HLS、EXR/TIFF 预览，缓存与资源限制。

默认服务端处理；ffmpeg + libvips + OpenImageIO；缓存键=资产 hash+profile；独立容器限制 CPU/内存/超时；EXR tone-map、TIFF 多页、MOV/MKV 转代理；API 只返回预览地址。

## 非职责

不打包 ZIP、不改元数据、不直接对公网。

## 依赖

contracts, storage

## 接口

PreviewProvider：probe / generate / delete

## 失败模式

解码失败、OOM、超时、缓存失效、格式不支持。

## 测试

格式矩阵、输出可播放/可解码、缓存、资源限制、失败回退。

## 替换点

ffmpeg/libvips/oiiotool 提供者可替换，接口不变。
