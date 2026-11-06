# agent-gate 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

文档/history/wiki/schema/链接/契约门禁，pre-commit 与 CI。

检查每次提交是否有 history、模块 history、docs/wiki impact 一致；检查 module.yaml、索引、链接、禁止历史进 docs；按 commit 遍历；不替代测试。

## 非职责

不做业务测试、不判断内容语义正确性。

## 依赖

仓库自身

## 接口

check 命令；commit 遍历

## 失败模式

漏写 history、impact 声明不实、链接失效、索引缺失。

## 测试

夹具仓库、错误提交、CI。

## 替换点

工具可替换；规则文档化。

## Phase 0 实现

- CLI：`python3 modules/agent-gate/src/agent_gate.py check --staged`
- 支持 `--base <ref>` 按 commit 遍历，`--all` 只做结构/链接检查。
- 检查根 `history/commits` 记录、模块 history、docs/wiki impact、module.yaml、Markdown 相对链接。
- pre-commit：`.githooks/pre-commit`；安装：`git config core.hooksPath .githooks`。
- CI：`.github/workflows/agent-gate.yml`。
- 依赖：`modules/agent-gate/requirements.txt` 中的 PyYAML。
- 尚未实现：OpenAPI/JSON Schema 内容校验、提交记录 diff 语义审查。
