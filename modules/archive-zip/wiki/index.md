# archive-zip 模块（人类说明）

archive-zip 只负责把字节装进 ZIP，并保证 ZIP 里没有多余的时间字段。它不关心 EXR 或 MP4 内部有什么。

## 什么时候会用到

pipeline 已经算好每个条目的时间、准备好字节流之后，把它们交给 archive-zip。

## 一个最小例子

```python
from moyu_archive_zip import ArchiveWriter, verify_archive

dos = (2026, 1, 2, 3, 4, 4)
with ArchiveWriter("delivery.zip") as writer:
    writer.add_file("frames/0001.exr", dos, "frames/0001.exr")

result = verify_archive("delivery.zip", {"frames/0001.exr": {"dos": dos}})
assert result["ok"], result["problems"]
```

`dos` 的秒必须是偶数；如果写入过程中源文件变化，`add_file` 会报错。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/`：跨模块契约。