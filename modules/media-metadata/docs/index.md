# media-metadata 模块文档

状态：v0.0.1 阶段 1 最小实现（Python）。

## 职责

识别媒体格式，探测内部时间字段，生成等长补丁或 materialize 重建计划，并在写 ZIP 时流式应用。

覆盖 EXR、PNG、JPEG、TIFF、WebP、AVIF、MP4/MOV、MKV。常规字段走等长补丁；PNG 压缩 zTXt/iTXt 需要解压、改写、重压缩并重建 chunk/CRC。默认尽量不改变像素/媒体流；无法确认的元数据在严格模式下失败。

## 非职责

不负责 ZIP 结构、不负责 Web 预览、不修改源文件作为默认行为。

## 依赖

contracts, core-time

## 接口

Python 包位于 `src/moyu_media_metadata/`，对外导出：

- `detect_format(path) -> str | None`
- `build_metadata_patches(path, target_epoch, tz) -> MetadataInfo`
- `apply_patches(data, patches) -> bytes`
- `iter_patched_chunks(path, patches, chunk_size) -> Iterator[bytes]`
- `materialize_metadata(path, info, target_epoch, tz, dest_dir) -> str | None`
- `patch_to_dict(patch) -> dict`
- `MetadataError` / `MetadataInfo` / `Patch` / `FileReader` / `BytesReader`

适配器注册表：

- `ADAPTERS`：格式名到 `Adapter` 的映射。
- `adapter_by_name(name)` / `adapter_for(path)`。
- `Adapter.detect(header)` / `inspect(path, target_epoch, tz)` / `plan(...)` / `apply(data, plan)` / `stream(...)` / `materialize(...)`。

`MetadataInfo` 包含 `format`、`patches`、`records`、`notes`、`strict_problems`、`requires_materialize`。补丁必须等长且区间不重叠。

## 配置

时间目标由调用方传入 `target_epoch` 与时区对象，本模块不读取配置、不使用系统本地时区。

## 失败模式

格式损坏、边界不完整、补丁长度不一致、未知压缩方法、AVIF idat/多 extent 不支持。无法识别的格式返回 `format="unknown"` 并记录 `strict_problems`。

## 测试

`tests/test_media_metadata.py` 覆盖：

- 图片矩阵改写后长度不变、区间外字节不变、Pillow 可解码、PNG CRC 合法；
- MP4 合成容器的 `mvhd`/`tkhd`/`mdhd`/`©day`；
- PNG 压缩 `zTXt` 的 materialize、源文件不变、输出可解码；
- MP4/MOV/MKV 视频素材（素材存在时）；
- 未知格式的严格问题；
- 适配器 header 识别与 `adapter_for`。

运行：

```bash
python3 -m unittest discover -s modules/media-metadata/tests -v
```

素材缺失时依赖素材的用例会跳过；合成用例始终运行。

## 替换点

每个格式一个 adapter；可替换为 Rust/WASM/外部工具，但必须通过同一套 conformance。