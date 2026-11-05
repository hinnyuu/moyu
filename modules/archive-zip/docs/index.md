# archive-zip 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

写交付 ZIP：DOS mtime、安全条目名、ZIP64、无时间类 extra field、CRC 与原子改名。

默认 STORE，不压缩；条目时间只写 DOS mtime；允许 ZIP64 `0x0001`，拒绝 `0x5455`、`0x000a`、`0x5855`、`0x000d` 等时间字段；写 `.part`，校验通过后原子改名。未来 Rust 实现通过 JSON job spec + 进度事件使用同一契约。

## 非职责

不解析媒体格式、不计算时间策略、不负责上传。

## 依赖

contracts

## 接口

ArchiveWriter：add_entry / finalize / verify

## 失败模式

磁盘不足、源文件变化、extra field 泄漏、DOS 时间非法、ZIP64 异常。

## 测试

条目名/DOS 时间/extra field/CRC/ZIP64、>4GiB、>65535 条目、原子性。

## 替换点

Python 实现可换 Rust；语义 conformance 不要求 ZIP 字节完全一致。
