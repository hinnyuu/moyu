# moyu Agent 维护规则

本仓库从 `v0.0.1` 开始按“便于 agent 长期维护”的方式组织。当前分支是 `draft/v0.0.1-architecture`，只包含架构、规划、契约和 wiki 草稿，不包含新业务实现。

## 阅读顺序

1. 根 `README.md`：项目入口和当前阶段。
2. `docs/architecture/overview.md`：整体架构和边界。
3. `docs/architecture/runtime-topology.md`：镜像、容器、Podman pod、端口和部署形态。
4. `docs/architecture/modules.md`：模块清单、依赖和替换边界。
5. `docs/contracts/`：跨模块契约。
6. `modules/<模块>/README.md`：模块入口。
7. `modules/<模块>/docs/`：该模块当前事实。
8. `modules/<模块>/history/`：该模块历史，按时间追加，只读。
9. `modules/<模块>/wiki/`：该模块的人类可读解释、教程和排错。

## 三条硬规则

### 1. 文档、history、wiki 严格分离

| 目录 | 只放什么 | 禁止放什么 |
| --- | --- | --- |
| `docs/` | 当前真实架构、接口、配置、数据模型、运维事实 | 日期流水账、变更日志、“以前是这样” |
| `history/` | 每次提交/决策的时间、原因、影响、迁移、测试 | 当前接口规范、教程正文 |
| `wiki/` | 通俗解释、操作教程、示例、FAQ、排错 | 变更流水账、发布日志 |

根级 `docs/history/wiki` 只写项目级内容；模块级细节写在模块自己的三件套里。根级索引可以链接模块内容，但不复制正文。

### 2. 每次提交维护文档、history 和 wiki

每次提交必须：

- 在 `history/commits/` 增加一条提交记录；
- 为每个被修改的模块增加模块级 `history/` 记录；
- 在提交记录中声明 `docs_impact`、`wiki_impact` 以及原因；
- 当影响为 true 时，实际修改对应 `docs/`、`wiki/` 文件；
- 当影响为 false 时，写清楚为什么不需要改。

`agent-gate` 会在 pre-commit 和 CI 中检查。不要用“补一个空文件”的方式绕过门禁。

### 3. 模块边界

- 一个模块只拥有自己的实现、文档、history、wiki 和测试。
- 模块之间只通过 `contracts` 中的接口和协议通信。
- 禁止直接 import 其他模块的内部实现。
- 替换一个模块时，其他模块不应需要改业务代码，只改装配配置。
- 模块文档必须说明：职责、接口、依赖、配置、失败模式、测试方式、可替换点。

## 提交前检查清单

- [ ] 代码/文档改动是否属于当前模块？
- [ ] 是否新增或更新了 `history/commits/` 记录？
- [ ] 每个受影响模块是否有 `history/` 记录？
- [ ] `docs_impact` / `wiki_impact` 是否与实际改动一致？
- [ ] 是否把历史流水账写进了 `docs/`？
- [ ] 是否把当前接口规范写进了 `history/`？
- [ ] 是否新增了硬编码端口、路径、密钥或镜像标签？
- [ ] 是否更新了对应模块的 `module.yaml` 索引？
- [ ] 测试和契约校验是否通过？

## 配置、端口和密钥

- 端口、路径、存储根、证书路径等必须是配置项，不得在代码或文档中写死。示例中的端口只是占位符。
- 配置写入 `/config` 持久目录；缺少时补默认；损坏时优先加载 `state/last-known-good`。
- Secret 独立存放，不进普通 YAML；WebUI 生成/轮换后只展示一次。
- WebUI 不直接控制 Podman socket；部署拓扑由 Quadlet/pod YAML 管理。

## Rust workspace

- 一个 Cargo workspace，三个独立 crate：`gateway`、`wasm-client`、`core-rust`。
- `gateway` 与 `wasm-client` 不互相依赖，只共享 target-neutral 的 `core-rust`。
- 每个 crate 的文档、history、wiki 仍在对应模块目录下。
- 不要把网关和 WASM 合并成一个 crate，也不要把原生依赖带进 WASM target。

## 版本与分支

- 架构冻结前不打 `v0.0.1` 标签。
- 架构草稿在 `draft/v0.0.1-architecture` 分支。
- 合并到 `main` 后再开始业务实现；实现完成、端到端验收通过后才创建 `v0.0.1` release。

## 门禁命令

```bash
python3 modules/agent-gate/src/agent_gate.py check --staged
python3 modules/agent-gate/src/agent_gate.py check --base origin/main
```
