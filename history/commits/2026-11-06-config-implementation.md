---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - config
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/config/tests -v; agent-gate --staged
---

# config 阶段 2 最小实现

## 背景

api/worker/preview 需要稳定的运行配置入口：多文件、严格 schema、缺失补默认、损坏回退 LKG、写入原子化并带 revision。

## 改动

- 新增 `modules/config/src/moyu_config/`：`provider.py`、`defaults.py`、`errors.py`。
- 实现 `ConfigProvider.load / validate / write / last_known_good`。
- 实现多文件默认值写入、YAML anchor/alias 拒绝、JSON Schema 严格校验。
- 实现 `state/last-known-good/` 快照与 `state/backups/` 备份、临时文件 + fsync + rename。
- 实现深合并 patch、`null` 删除字段、revision 冲突检测。
- 新增 9 个单元测试。
- Python CI 增加 `jsonschema` 依赖。
- 更新 config 的 README、docs、wiki 和 `module.yaml`。

## 影响

- 运行时配置有了统一入口；业务模块不再直接读 YAML。
- 默认值集中在 `defaults.py`，端口/路径是可编辑默认值，不是固定事实。
- secret 目录不由本模块读写。
- 尚未接入 WebUI、审计数据库和 schema 迁移器。

## 验证

- `python3 -m unittest discover -s modules/config/tests -v`：9 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。