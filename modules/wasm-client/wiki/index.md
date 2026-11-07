# wasm-client 模块（人类说明）

wasm-client 是“浏览器本地处理”的可选模式。它能少上传、离线预览，但不是所有格式/大文件都适用。

## 什么时候会用到

浏览器想在上传前直接生成交付 ZIP 时。它只写 DOS mtime，适合小文件；大文件和内部元数据改写仍走服务端。

## 最小用法

```rust
use moyu_wasm_client::{pack, ClientFile};

let files = vec![ClientFile::new("a.txt", 1_799_999_900_000_000_000, b"hi".to_vec())];
let zip = pack(&files, 1_800_000_000, 0).expect("zip");
```

浏览器侧先通过 `wasm-bindgen` 生成 JS glue，再使用 `PackBuilder`。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/`：跨模块契约。
