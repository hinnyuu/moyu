# pipeline 模块（人类说明）

pipeline 把三件事串起来：算时间、改媒体元数据、写 ZIP。

## 什么时候会用到

worker 拿到一个打包任务时调用 pipeline。它不关心 HTTP、上传或数据库，只接收输入文件列表和目标时间。

## 一个最小例子

```python
from moyu_pipeline import PackInput, pack

pack(
    [PackInput("frames/0001.exr", "frames/0001.exr")],
    target_epoch=1790000000,
    output="delivery.zip",
    timezone="Asia/Shanghai",
    manifest_path="delivery.json",
)
```

成功后 `delivery.zip` 的条目时间被改成目标时间，`delivery.json` 记录每个条目的 DOS 时间、元数据字段和归档 sha256。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/`：跨模块契约。