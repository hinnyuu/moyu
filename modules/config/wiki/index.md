# config 模块（人类说明）

config 是配置的“总入口”。WebUI 看起来是一个页面，背后是多个模块配置文件、默认值、校验和备份。

## 什么时候会用到

api、worker、preview、gateway 启动时读取配置；WebUI 保存配置时调用 `write`。

## 一个最小例子

```python
from moyu_config import ConfigProvider

provider = ConfigProvider("/config")
effective = provider.load()
print(effective.modules["worker"]["concurrency"])

result = provider.write(
    "worker",
    {"concurrency": 4},
    revision=effective.revisions["worker"],
)
print(result.revision)
```

如果文件被其他人改过，`revision` 不匹配会报 `revision_conflict`，不会覆盖。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/config.md`：配置契约。