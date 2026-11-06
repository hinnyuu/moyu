---
date: 2026-11-06
module: core-time
commit: (included in this commit)
---

# core-time Python 参考实现

## 改动

- 新增 `python/moyu_core_time/`，镜像 Rust 的时间计划、DOS 转换和错误码。
- 新增 `tests/test_core_time.py`，8 个用例覆盖 DOS 字、公历转换、固定 offset、目标时间约束和空输入。
- 更新模块 docs/wiki/README/module.yaml。

## 影响

- Python 与 Rust 使用同一套语义；时区偏移由调用方计算后传入。
- 不引入文件 I/O、数据库或网络依赖。