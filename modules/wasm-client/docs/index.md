# wasm-client 模块文档

状态：v0.0.1 架构草稿，尚未实现。

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

## Rust 骨架

- workspace member：`modules/wasm-client/rust`，package `moyu-wasm-client`，crate-type `cdylib + rlib`。
- 当前只有无逻辑占位，不包含 ZIP/转码。
- 沙箱没有 cargo/rustc；实现阶段用 `wasm-pack` 构建并验证 target 依赖隔离。
- v0.0.1 客户端 ZIP 只承诺 DOS mtime，不承诺内部元数据改写。
