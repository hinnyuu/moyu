# 开发：模块维护流程

## 1. 开始前

读：

1. 根 `AGENTS.md`
2. `docs/architecture/overview.md`
3. `docs/architecture/modules.md`
4. 目标模块的 `README.md` / `docs/index.md` / 最近 history
5. 相关 `docs/contracts/`

## 2. 修改范围

- 一次只改一个模块；跨模块先改 contracts。
- 不直接 import 其他模块内部实现。
- 不硬编码端口/路径/镜像 tag。
- 不修改源文件作为默认行为。
- Secret 不进普通配置。

## 3. 文档三件套

每次提交：

- 根 `history/commits/<日期>-<slug>.md`
- 每个受影响模块 `history/<日期>-<slug>.md`
- 更新 docs（当前事实）
- 更新 wiki（人类教程）
- 提交记录声明 docs/wiki impact

## 4. 测试

- 单元 + conformance + 集成
- 媒体格式：像素/码流不变、CRC、可解码
- Podman：端口、卷、TLS、IPv6
- 文档门禁：agent-gate

## 5. 替换模块

1. 读 contracts + conformance
2. 新实现通过同一套 conformance
3. 只改装配
4. ADR + history
5. 更新 docs/wiki

## 6. 禁止

- 把历史流水账写进 docs/wiki
- 把当前接口规范写进 history
- 为空文件过门禁
- WebUI 直接控制 Podman
- 网关和 WASM 合并一个 crate
- 写死端口

## 门禁

```bash
python3 modules/agent-gate/src/agent_gate.py check --staged
```

安装 hook：

```bash
git config core.hooksPath .githooks
```

门禁只检查文档结构和历史完整性，不评价代码实现。
