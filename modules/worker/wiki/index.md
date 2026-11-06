# worker 模块（人类说明）

worker 是真正干打包重活的角色。它从队列拿任务，跑完把结果写回，不和 API 抢请求处理。

## 什么时候会用到

worker 是真正干打包重活的角色。它从队列拿任务，跑完把结果写回，不和 API 抢请求处理。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/`：跨模块契约。
