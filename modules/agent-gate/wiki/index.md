# agent-gate 模块（人类说明）

agent-gate 是“文档门禁”。它不评价代码好坏，只确保文档、history、wiki 没有漏、没有混。

## 什么时候会用到

agent-gate 是“文档门禁”。它不评价代码好坏，只确保文档、history、wiki 没有漏、没有混。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/`：跨模块契约。

## 怎么用

```bash
python3 modules/agent-gate/src/agent_gate.py check --staged
python3 modules/agent-gate/src/agent_gate.py check --base origin/main
```

它只检查“文档/history/wiki 有没有漏、有没有混”，不评价代码质量。
