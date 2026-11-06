---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - uploads
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/uploads/tests -v; agent-gate --staged
---

# uploads 阶段 2 最小实现

## 背景

storage 已提供上传目录和 `upload_sessions` 表，需要在其上实现 tus 断点续传语义与完成入库。

## 改动

- 新增 `modules/uploads/src/moyu_uploads/`：`UploadSessionStore`、`UploadSession`、`UploadError`。
- 实现创建会话、顺序分片追加、偏移校验、声明大小校验、配额检查、完成入库、取消与过期清理。
- 会话元数据写入 `uploads/<id>/meta.json`；偏移和状态复用 storage 的 SQLite 表。
- 新增 7 个单元测试。
- 更新 uploads 的 README、docs、wiki 和 `module.yaml`。

## 影响

- 上传层可以独立于 HTTP 框架测试；tusd 完成钩子可直接调用 `finish_session`。
- 完成上传后文件移动为资产，会话目录与数据库行删除。
- 尚未实现 tus HTTP 端点、上传 token 与批次管理。

## 验证

- `python3 -m unittest discover -s modules/uploads/tests -v`：7 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。