# uploads 模块（人类说明）

uploads 负责“文件一点点传上来，最后变成一个资产”。

## 什么时候会用到

浏览器或 tusd 每上传一个分片，调用 `append_chunk`；传完后调用 `finish_session`。

## 一个最小例子

```python
from moyu_storage import Storage
from moyu_uploads import UploadSessionStore

storage = Storage("/data").ensure_layout()
uploads = UploadSessionStore(storage, max_upload_bytes=2 * 1024**3)

session = uploads.create_session({"filename": "frame.exr", "size": 3})
uploads.append_chunk(session.id, 0, b"abc")
asset = uploads.finish_session(session.id)
print(asset.id)
```

分片必须按顺序到达；偏移不对会报错，不会覆盖已有数据。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/module-interfaces.md`：UploadSessionStore 契约。