# preview

媒体探测、图片缩略图/代理、视频 poster/MP4/HLS、EXR/TIFF 预览，缓存与资源限制。

- 当前状态：v0.0.1 阶段 2 最小实现（Pillow，图片）。
- 依赖：contracts, storage
- 接口：PreviewProvider：probe / generate / delete
- 实现：`src/moyu_preview/`
- 测试：`tests/test_preview.py`

阅读顺序：`docs/index.md` → `history/index.md` → `wiki/index.md`。