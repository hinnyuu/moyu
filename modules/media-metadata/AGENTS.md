# media-metadata 模块 Agent 规则

1. 只改本模块；跨模块先改 `contracts`。
2. 不直接 import 其他模块内部实现。
3. 不写死端口、路径、镜像 tag、密钥。
4. 每次提交更新本模块 `history/`，并同步 `docs/`、`wiki/`（如适用）。
5. 模块接口和替换点必须与 `docs/contracts/` 一致。
6. 不把历史流水账写进 `docs/` 或 `wiki/`。

阅读：本模块 `docs/index.md`、`history/index.md`、`wiki/index.md`，以及根 `AGENTS.md`。
