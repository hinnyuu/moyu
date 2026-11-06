# storage 模块（人类说明）

storage 管理“文件放在哪里、任务现在什么状态、空间还够不够”。

## 什么时候会用到

上传完成时登记资产；worker 创建任务、更新进度、写输出；清理旧上传和预览缓存。

## 一个最小例子

```python
from moyu_storage import AssetStore, JobStore, Storage

storage = Storage("/data", quota_bytes=0).ensure_layout()
assets = AssetStore(storage)
asset = assets.register_asset("/tmp/upload.bin", original_name="upload.bin")

jobs = JobStore(storage)
job = jobs.create_job({"inputs": [asset.id], "output": "delivery.zip"})
jobs.update_status(job.id, "queued")
jobs.update_status(job.id, "running", progress=10)
```

所有 ID 由 storage 生成；数据根目录来自配置，不写死在业务模块里。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/module-interfaces.md`：JobStore / AssetStore 契约。