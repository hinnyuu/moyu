---
date: 2026-11-06
module: worker
commit: (included in this commit)
---

# 只读配置

## 改动

- `python -m moyu_worker` 使用 `ConfigProvider(..., read_only=True)`。

## 影响

- worker 容器可以只读挂载 `/config`，不会尝试写默认文件或 LKG。
- 运行逻辑与轮询不变。