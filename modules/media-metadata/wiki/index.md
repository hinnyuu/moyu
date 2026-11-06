# media-metadata 模块（人类说明）

media-metadata 只回答一个问题：这个文件里有哪些时间字段，能不能在不改变像素或媒体流的前提下把它们改掉。

## 什么时候会用到

打包交付 ZIP 时，pipeline 调用本模块生成补丁计划，再把补丁流交给 archive-zip。源文件始终只读。

## 一个最小例子

```python
import moyu_media_metadata as md
from zoneinfo import ZoneInfo

tz = ZoneInfo("Asia/Shanghai")
info = md.build_metadata_patches("frame.png", 1790000000, tz)
if info.strict_problems:
    raise SystemExit(info.strict_problems)

for chunk in md.iter_patched_chunks("frame.png", info.patches):
    ...  # 写入 ZIP 条目
```

`info.requires_materialize` 为真时不能直接套补丁，要调用 `materialize_metadata` 生成临时文件。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/`：跨模块契约。