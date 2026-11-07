# wasm-client 模块文档

状态：v0.0.1 阶段 2 最小实现（Rust core + WASM 绑定）。

## 职责

可选浏览器 ZIP/预览转码；Rust WASM，懒加载，不是默认路径。

Rust crate 与 gateway 共用 workspace；客户端 ZIP v0.0.1 只保证 DOS mtime，不承诺内部元数据改写；转码用于本地预览；能力检测/OPFS/COOP-COEP；失败回退服务端。

## 非职责

不替代服务端默认处理；不承诺完整元数据清洗；不处理大视频/8K EXR。

## 依赖

contracts, core-time

## 接口

WasmPackClient：capabilities / pack / transcode

## 失败模式

不支持 WASM/SharedArrayBuffer、内存不足、浏览器 codec 缺失、OPFS 不可用。

## 测试

Chromium feature detection、客户端 ZIP conformance、预览回退、内存/大小限制。

## 替换点

可禁用/替换；Rust crate 与 gateway 不互相依赖。

## 实现

workspace member：`modules/wasm-client/rust`，package `moyu-wasm-client`，`cdylib + rlib`。

Rust 核心：

- `ClientFile { name, mtime_ns, data }`
- `pack(files, target_epoch, utc_offset_seconds) -> Result<Vec<u8>, PackError>`
- `write_zip(entries)`：STORE、UTF-8 名称、DOS mtime、无 extra field、标准 CRC32。
- 复用 `moyu-core` 的 `plan_times`：所有文件同一 delta，最新文件对齐目标时间，DOS 秒向下取整。

WASM 绑定（`cfg(target_arch = "wasm32")`）：

- `PackBuilder`：`new()`、`add_file(name, mtime_ns, data)`、`finish(target_epoch, utc_offset_seconds)`；
- `transcode(data, maxWidth, maxHeight, format, quality)`：图片缩放/编码（png/jpeg）；
- `capabilities()`：返回 JSON 字符串（STORE、DOS-only、上限）；
- 需要 `wasm-bindgen` CLI 生成 JS glue；镜像 `wasm` 阶段用 `cargo install wasm-bindgen-cli --version 0.2.130`，再 `cargo build` + `wasm-bindgen --target web` 输出到 `/opt/moyu/web/wasm`。
- 本地构建脚本：`modules/web/app/scripts/build-wasm.sh`（需要同版本 wasm-bindgen CLI），输出到 `public/wasm/`（不提交）。
- Web 动态加载 `/wasm/moyu_wasm_client.js`；i64 参数在 JS 侧使用 `BigInt`。

限制：

- 只支持 STORE，不压缩；
- 总输入默认 512MiB，条目数 65535，单条 4GiB；
- 只改 DOS mtime，不承诺内部媒体元数据；
- 转码只支持图片（PNG/JPEG 输出）；视频转码未实现，调用方回退服务端。

## 测试

```bash
cargo test -p moyu-wasm-client
cargo clippy -p moyu-wasm-client --all-targets -- -D warnings
cargo check -p moyu-wasm-client --target wasm32-unknown-unknown
```

8 个单元测试覆盖 ZIP 结构、无 extra、同一 delta、偶数秒、非法名称、目标时间与空输入、CRC32、PNG→JPEG/PNG 转码与错误格式。
