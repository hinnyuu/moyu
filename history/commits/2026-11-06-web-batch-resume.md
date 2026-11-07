---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: true
wiki_impact: false
wiki_reason: 队列/续传已在模块 docs 说明，未改变整体操作教程结构
breaking: false
tests: npm run typecheck; npm test; npm run build; agent-gate --staged
---

# Web 批量队列与断点续传

## 背景

发布前审计要求 Web 支持批量队列与断点续传；此前 Upload 页只能单文件上传，刷新后无法恢复。

## 改动

- 新增 `queue.ts`：
  - 队列元数据存 `localStorage`；
  - 文件 Blob 存 IndexedDB；
  - `uploadItem` 支持新建会话、按服务器 offset 续传、分片、暂停、完成。
- Upload 页改为多文件队列：
  - 添加多个文件、开始/恢复全部、暂停、单个上传、移除；
  - 刷新后恢复队列并把 `uploading` 置为 `paused`；
  - 完成后选择资产创建任务。
- API 客户端增加 `getUpload`。
- 新增 Vitest 4 个队列测试；`web` workflow 增加 `npm test`。
- 更新 Web docs、module.yaml、root README。

## 影响

- 刷新/断网后可从服务器偏移量继续上传。
- Blob 存 IndexedDB，清理浏览器数据会丢失本地缓存。
- WASM 接入仍未完成。

## 验证

- `npm run typecheck`：通过。
- `npm test`：4 passed。
- `npm run build`：通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
