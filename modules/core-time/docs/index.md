# core-time 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

时间策略、目标时间映射、DOS/EXIF/QuickTime/Matroska 时间换算，以及 target-neutral 的 Rust core crate。

输入源文件 mtime 和目标时间，输出统一的 TimePlan。所有文件使用同一个 delta，保持相对顺序；最新文件对齐目标时间；DOS 时间按 2 秒向下取整。时区使用 IANA 名称，内部计算以 epoch 为准。Rust crate 只放目标无关逻辑，不引入 tokio、文件系统、TLS。

## 非职责

不做文件 I/O、不读媒体元数据、不写 ZIP、不访问数据库。

## 依赖

contracts

## 接口

TimePolicy、PackPlan 时间字段；Rust `moyu-core`

## 失败模式

目标时间早于最新源 mtime、DOS 时间越界、时区无效。

## 测试

固定时间向量、跨时区、亚秒间隔、2038/2107 边界。

## 替换点

纯函数实现可替换；Rust 与 Python 实现必须通过同一套时间向量 conformance。
