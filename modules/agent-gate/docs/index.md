# agent-gate 模块文档

状态：已实现，v0.0.1 发布前持续维护。

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
- 相对链接检查跳过 `.git`、`node_modules`、`dist`、`target`、`.venv`、`__pycache__`，避免第三方 README 误报。
- pre-commit：`.githooks/pre-commit`；安装：`git config core.hooksPath .githooks`。
- CI：`.github/workflows/agent-gate.yml`。
- 依赖：`modules/agent-gate/requirements.txt` 中的 PyYAML。
- 尚未实现：OpenAPI/JSON Schema 内容校验、提交记录 diff 语义审查。

## PR 检查

GitHub `pull_request` 事件默认 checkout 的是临时 merge commit，不是 PR head。临时 merge commit 没有项目 history，直接检查会误报“缺少 history/commits 记录”。

workflow 因此在 PR 中显式 checkout：

```text
repo = head repo
ref  = pull_request.head.sha
```

push 事件仍使用 `github.ref`。这样 agent-gate 始终检查真实提交，而不是 GitHub 的临时合并提交。

## 空范围与 merge commit

- 提交范围为空是合法的：表示当前 HEAD 没有待检查提交，不报错。
- 多父 merge commit 是 GitHub/项目合并产物，不代表独立功能提交；agent-gate 跳过它的 history 检查。
- PR 的普通提交由 head 提交逐个检查；合并提交不需要重复写 history。
- push 工作流使用 `github.event.before` 作为 base，检查本次推送实际包含的提交；首次 push/空 before 回退到 `origin/main`。
