# wasm-client

可选浏览器 ZIP/预览转码；Rust WASM，懒加载，不是默认路径。

- 当前状态：核心、WASM 绑定、镜像产物与 Web 懒加载已实现；Rust 图片转码已实现，Web 视频转码走 ffmpeg.wasm。
- 依赖：contracts, core-time
- 接口：WasmPackClient：capabilities / pack / transcode

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。
