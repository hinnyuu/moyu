# Agent Playbook

本文件说明 agent 在本仓库中如何阅读、修改、测试和提交。目标不是“写得快”，而是“长期可维护、可追溯、可替换”。

## 1. 开始工作前

1. 读根 `AGENTS.md`。
2. 读 `docs/architecture/overview.md` 和 `modules.md`。
3. 找到要改的模块，读：
   - `modules/<模块>/README.md`
   - `modules/<模块>/docs/index.md`
   - 最近 1–3 条 `modules/<模块>/history/`
   - 相关 `docs/contracts/`
4. 如果涉及跨模块接口，先改 `contracts` 文档，再改实现。
5. 如果涉及部署、端口、配置、证书，先读对应 wiki 和 contracts。

## 2. 修改规则

- 一次只改一个模块；跨模块改动必须在提交记录里列出所有受影响模块。
- 不直接 import 其他模块内部实现；通过 contracts。
- 不改硬编码端口、路径、镜像 tag；用配置。
- 不把 secret 写进普通 YAML。
- 不把历史流水账写进 `docs/`。
- 不把当前接口规范写进 `history/`。
- 模块新增/替换必须更新 `module.yaml` 和模块索引。
- 破坏性接口变更必须有 ADR。

## 3. 文档、history、wiki

每个提交至少：

- 根 `history/commits/<日期>-<slug>.md`；
- 每个受影响模块的 `history/<日期>-<slug>.md`；
- 提交记录中声明：
  ```yaml
  docs_impact: true|false
  wiki_impact: true|false
  docs_reason: ...
  wiki_reason: ...
  ```
- `docs_impact: true` 时实际修改 docs；
- `wiki_impact: true` 时实际修改 wiki；
- 如果为 false，写清楚为什么不需要。

文档写法：

- docs：当前事实，现在时；
- history：时间、原因、影响、迁移、测试；
- wiki：通俗解释、教程、示例、FAQ。

## 4. 测试

- 单元测试：每个模块自己。
- 契约/conformance：接口语义。
- 集成测试：Podman pod、卷、端口、TLS、IPv6。
- 媒体测试：格式覆盖、像素/码流不变、CRC、可解码性。
- 文档门禁：`agent-gate`。
- 没有测试的改动不能视为完成。

## 5. 提交

- 分支命名：`feat/...`、`fix/...`、`docs/...`、`draft/...`。
- 每个提交聚焦一个主题。
- 提交记录先写，再提交；不要事后补。
- CI 会按 commit 检查 history/docs/wiki，合并前必须通过。
- 不创建版本标签，除非明确进入 release 流程。

## 6. 跨模块替换

如果要替换模块：

1. 读该模块的 contracts 和 conformance；
2. 新实现必须通过同一套 conformance；
3. 只改装配配置，不改其他模块业务代码；
4. 写 ADR + history；
5. 更新 docs/wiki 的替换说明。

## 7. 禁止事项

- 不要在 docs 里写“本次修改/以前是/迁移记录”。
- 不要在 history 里复制完整接口规范。
- 不要为了过门禁写空文件。
- 不要让 WebUI 直接控制 Podman socket。
- 不要把网关和 WASM 合并成一个 crate。
- 不要在代码或文档里写死端口；示例端口只是占位符。
- 不要修改用户源文件作为默认行为。