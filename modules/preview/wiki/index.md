# preview 模块（人类说明）

preview 负责把资产变成能快速显示的缩略图或代理图，并按资产 hash + profile 缓存。

## 什么时候会用到

WebUI 展示上传的图片、任务输出或资产列表时，API 返回预览地址，preview 生成并缓存文件。

## 一个最小例子

```python
from moyu_preview import PreviewProvider
from moyu_storage import Storage

storage = Storage("/data").ensure_layout()
previews = PreviewProvider(storage)

info = previews.probe(asset_id)
artifact = previews.generate(asset_id, "thumb")
print(artifact.path)
```

视频和 EXR 目前会返回“不支持”，等 ffmpeg / OpenImageIO 接入后再开放。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/module-interfaces.md`：PreviewProvider 契约。