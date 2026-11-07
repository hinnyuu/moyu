---
date: 2026-11-06
module: wasm-client
commit: (included in this commit)
---

# wasm-client 阶段 2 最小实现

## 改动

- 新增 STORE ZIP 写入器与 CRC32。
- `pack()` 复用 core-time 计算统一 delta 和 DOS 时间。
- WASM `PackBuilder` 与 `capabilities()` 绑定。
- 6 个单元测试覆盖结构、delta、偶数秒、非法名称、目标时间、CRC。

## 影响

- 客户端 ZIP 核心可测试、可编译到 wasm32。
- 尚未产出浏览器可直接使用的 wasm/js 包，也未接入 WebUI。