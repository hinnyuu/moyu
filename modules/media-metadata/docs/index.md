# media-metadata 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

识别媒体格式，探测内部时间字段，生成等长补丁或 materialize 重建计划，并在写 ZIP 时流式应用。

覆盖 EXR、PNG、JPEG、TIFF、WebP、AVIF、MP4/MOV、MKV。常规字段走等长补丁；PNG 压缩 zTXt/iTXt 需要解压、改写、重压缩并重建 chunk/CRC。默认尽量不改变像素/媒体流；无法确认的元数据在严格模式下失败。

## 非职责

不负责 ZIP 结构、不负责 Web 预览、不修改源文件作为默认行为。

## 依赖

contracts, core-time

## 接口

MetadataAdapter：detect / inspect / plan / apply

## 失败模式

格式损坏、边界不完整、补丁长度不一致、未知压缩方法、AVIF idat/多 extent 不支持。

## 测试

格式矩阵、补丁区间外字节一致、Pillow 解码、PNG CRC、严格模式拒绝、MP4/MKV 容器结构。

## 替换点

每个格式一个 adapter；可替换为 Rust/WASM/外部工具，但必须通过同一套 conformance。
