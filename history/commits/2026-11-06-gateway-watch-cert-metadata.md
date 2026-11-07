---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - gateway
docs_impact: true
wiki_impact: true
breaking: false
tests: cargo test -p moyu-gateway; cargo clippy -p moyu-gateway --all-targets -- -D warnings; watch runtime E2E; agent-gate --staged
---

# 网关 watch 与证书元数据

## 背景

发布前缺口：gateway watch 未实现，证书状态只有文件 SHA-256，未解析 serial/not_after。

## 改动

- 新增 `notify` watcher：监听证书/私钥所在目录，变化后重载。
- 新增 `x509-parser`：解析叶子证书 serial 与 not_after。
- CertStore 保存并在 reload 时更新 serial/not_after/sha256/loaded_at。
- 管理 API 状态与重载响应增加 `cert_serial`、`cert_not_after`。
- docs/contract/wiki/release checklist/发布说明同步。

## 影响

- `reload.watch: true` 时不再只是日志，而是实际文件监听。
- 证书状态可展示 serial 与到期时间。
- watch 可能对同一次替换触发多次重载；功能正确但可后续去抖。

## 验证

- gateway 5 tests 通过；clippy 通过。
- 运行 E2E：替换证书后 `reloads` 从 0 增加，serial/sha256 变化。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
