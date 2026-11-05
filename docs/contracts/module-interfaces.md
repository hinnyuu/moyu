# 模块接口契约（草稿）

本文件定义模块之间的稳定边界。实现可以换语言、换库、换进程，但接口语义不变。

## 1. 时间与 Pack Plan

### `TimePolicy`

输入：

```text
sources: [
  { id, path, mtime_ns }
]
target: now | "YYYY-MM-DD HH:MM:SS"
timezone: IANA 时区名
```

输出：

```text
TimePlan {
  timezone
  target_epoch
  delta_ns
  entries: [
    { id, source_mtime_ns, target_epoch, dos_time }
  ]
}
```

规则：

- 所有文件使用同一个 `delta`，保持相对 mtime 顺序和间隔。
- 最新文件的 `mtime` 对齐目标时间。
- DOS 时间精度 2 秒；向下取整。
- 目标时间必须晚于最新源 mtime；否则返回错误。
- 时区只影响“目标时间字符串”和 DOS 本地时间；容器内部时间以 epoch 为准。

### `PackPlan`

```text
PackPlan {
  archive_name
  entries: [
    {
      source
      arcname
      target_epoch
      dos_time
      metadata: {
        format
        mode: patches | materialize | none
        patches
        strict_problems
        notes
      }
    }
  ]
}
```

`PackPlan` 是 pipeline 交给 archive writer 的输入，不包含源文件内容。

## 2. 媒体元数据

### `MetadataAdapter`

每种格式实现一个 adapter，注册到 `media-metadata`。

```text
detect(header) -> bool
inspect(reader) -> MetadataReport
plan(reader, target_epoch, tz) -> PatchPlan
apply(reader, patch_plan) -> stream | materialized_path
```

`PatchPlan` 支持两种模式：

1. **equal-length patches**
   - `offset`, `old`, `new` 长度相同；
   - 可流式应用，不改变文件长度；
   - 适用于 EXR/PNG tEXt/JPEG COM/TIFF EXIF/MP4 ©day/MKV DATE 等。

2. **materialize**
   - 需要改变文件结构或长度；
   - 例如 PNG 压缩 `zTXt`/`iTXt` 解压、改写、重压缩、重建 chunk/CRC；
   - adapter 生成临时文件或流，ZIP 条目大小以 materialize 结果为准；
   - 源文件仍不修改。

要求：

- 不改像素/媒体流；
- 严格模式下，无法确认或无法改写的时间元数据必须报错；
- 错误信息包含格式、字段、原因；
- 所有字段都记录在 manifest 中。

### `MetadataReport`

```text
MetadataReport {
  format
  fields: [
    { name, offset, old, new, kind }
  ]
  needs_materialize
  strict_problems
  notes
}
```

## 3. 归档

### `ArchiveWriter`

```text
add_entry(arcname, dos_time, stream, metadata) -> void
finalize() -> ArchiveSummary
verify(path, manifest) -> VerifyResult
```

要求：

- 只写 DOS mtime；
- 不写时间类 extra field（`0x5455`/`0x000a`/`0x5855`/`0x000d` 等）；
- ZIP64 自动；
- 写入 `.part`，校验通过后原子改名；
- 输出条目名安全，不含绝对路径或 `..`；
- 支持 STORE 默认，可选 deflate。

未来 Rust 实现通过 JSON job spec + 进度事件 + 退出码实现同一契约。

## 4. 任务与存储

### `JobStore`

```text
create_job(request) -> Job
get_job(id) -> Job
list_jobs(filter) -> [Job]
update_status(id, status, progress, error) -> Job
cancel_job(id) -> Job
append_event(id, event) -> void
```

状态机：

```text
created → queued → running → verifying → succeeded
                         ↘ failed
created/queued/running → canceled
```

### `AssetStore`

```text
register_asset(upload_session) -> Asset
open_asset(id) -> reader
path_for(id) -> path
delete_asset(id) -> void
```

### `UploadSessionStore`

```text
create_session(metadata) -> session
get_offset(session_id) -> int
append_chunk(session_id, offset, data) -> int
finish_session(session_id) -> Asset
expire_sessions(ttl) -> void
```

tusd 实现通过完成钩子调用 `finish_session`；API 不直接写上传文件。

## 5. 预览

### `PreviewProvider`

```text
probe(asset) -> MediaInfo
generate(asset, profile) -> PreviewArtifact
delete(asset) -> void
```

`PreviewArtifact`：

- 图片缩略图/显示代理；
- 视频 poster、MP4 代理、HLS；
- 缓存键：`asset_hash + profile`；
- 资源限制、超时、并发上限由 provider 配置。

## 6. 配置

### `ConfigProvider`

```text
load(config_dir) -> EffectiveConfig
validate(effective) -> ValidationResult
write(module, patch, revision) -> ConfigResult
last_known_good() -> EffectiveConfig
```

- 只通过 `config` 模块读写；
- 业务模块不直接读 YAML；
- 运行配置与部署配置分离；
- 详情见 `config.md`。

## 7. 网关

### `GatewayAdmin`

```text
reload_cert() -> CertStatus
cert_status() -> CertStatus
rotate_token() -> TokenOnce
revoke_token() -> void
```

- `reload_cert` 只重读挂载证书；
- 不接受上传证书；
- token 明文只展示一次；
- 详情见 `gateway-admin-api.md`。

## 8. 浏览器 WASM

### `WasmPackClient`

```text
capabilities() -> {zip, transcode, opfs, shared_array_buffer}
pack(plan, files) -> Blob/OPFS artifact
transcode(file, profile) -> preview artifact
```

- 可选能力，默认关闭；
- 客户端 ZIP 只保证 DOS mtime，不承诺内部元数据改写；
- 能力检测失败时自动回退服务端；
- 不阻塞主链路。

## 9. 错误模型

所有模块使用统一错误结构：

```text
{
  code: string,
  message: string,
  module: string,
  details: object,
  retryable: bool
}
```

错误码使用稳定字符串，不依赖 UI 文案。UI 只负责翻译。