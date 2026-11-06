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

## PR 检查

PR 里 GitHub 会临时造一个 merge commit 来跑 CI。它不是你真正的提交，也没有 history。工作流会改为 checkout PR 的 head SHA，避免把这个临时提交当成项目提交检查。

## 空范围与 merge commit

main 已经合并后，`origin/main..HEAD` 可能为空，这是正常的，不是错误。PR 合并产生的多父 merge commit 也不会被要求单独写 history；真正功能提交在 PR head 里已经被检查。
