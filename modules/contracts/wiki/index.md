# contracts 模块（人类说明）

contracts 是模块之间的“合同”。它不干活，但决定别的模块怎么合作。修改契约前先想清楚谁会受影响，并写 ADR。

## 什么时候会用到

contracts 是模块之间的“合同”。它不干活，但决定别的模块怎么合作。修改契约前先想清楚谁会受影响，并写 ADR。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/`：跨模块契约。

## 当前契约

当前已有 `openapi/openapi.yaml` 和 JSON Schema。它们是模块之间的机器可读合同；修改前先写 ADR/history，并同步 docs。
