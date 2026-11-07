---
date: 2026-11-06
module: config
commit: (included in this commit)
---

# 只读加载模式

## 改动

- `ConfigProvider(..., read_only=True)`：不创建目录/默认文件，不写 LKG，`write` 抛 `read_only`。
- 缺失配置在只读模式下使用内存默认值。
- 新增 2 个测试：只读不写文件、只读目录不存在时报错。

## 影响

- worker 等只读消费者可以挂载只读 `/config`。
- API 仍使用读写模式。