---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - storage
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/storage/tests -v; agent-gate --staged
---

# storage 阶段 2 最小实现

## 背景

pipeline 已能打包，但 api/worker 还缺少资产登记、任务状态和配额管理。storage 先提供本地文件系统 + SQLite 的最小实现。

## 改动

- 新增 `modules/storage/src/moyu_storage/`：`Storage`、`AssetStore`、`JobStore`、`StorageError`。
- 数据布局：uploads/assets/jobs/outputs/preview + `state.db`。
- 实现 UUID 路径、路径逃逸防护、配额检查、资产 sha256、任务状态机、事件表、TTL 清理。
- 新增 7 个单元测试。
- 更新 storage 的 README、docs、wiki 和 `module.yaml`。

## 影响

- worker 可以创建任务、更新进度、写事件；上传完成后可登记资产。
- 清理只处理 uploads/preview，不删除资产与输出。
- 尚未接入 API、S3 适配器或任务队列。

## 验证

- `python3 -m unittest discover -s modules/storage/tests -v`：7 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。