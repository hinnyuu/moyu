# ADR-0003：文档、history、wiki 严格分离

- 状态：已接受（v0.0.1 架构草稿）
- 日期：2026-11-06

## 背景

面向 agent 长期维护，最大的风险是文档被历史流水账塞满，以及模块历史无法追溯。

## 决策

- 根级三棵树：
  - `docs/`：当前事实；
  - `history/`：只追加的时间线/ADR/release；
  - `wiki/`：人类教程。
- 每个模块也拥有自己的 `docs/history/wiki`。
- 每次提交必须：
  - 新增 `history/commits/` 记录；
  - 为每个受影响模块新增 history；
  - 声明 `docs_impact` / `wiki_impact` 及原因；
  - 影响为 true 时实际修改 docs/wiki。
- 使用 `agent-gate` 在 pre-commit 和 CI 校验。
- 不强制每次提交都虚假修改三个目录；采用语义门禁，避免噪声。

## 理由

- docs 保持当前事实，agent 注意力不被历史分散。
- history 可追溯，但不污染 docs。
- wiki 面向人类，允许教程和解释，不承担变更日志。
- 模块级三件套让 agent 可在没有全项目上下文时维护单个模块。

## 代价

- 每次提交需要写 history，token 成本高。
- 需要工具和模板支撑，否则容易流于形式。
- 语义门禁需要审查者判断 docs/wiki impact 是否合理。

## 替代方案

- 单一 README + CHANGELOG：简单但会混杂当前事实和历史。
- 只写 docs，不写 history：无法追溯。
- 字面强制每次触碰三个目录：会产生大量空话，不采用。