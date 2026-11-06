---
date: 2026-11-06
module: config
commit: (included in this commit)
---

# config 阶段 2 最小实现

## 改动

- 新增 `src/moyu_config/`：加载器、默认值、错误模型。
- `load` 创建目录与缺失默认文件，校验后写入 LKG；非法配置回退 LKG，无 LKG 则失败。
- `write` 支持 revision 冲突检测、深合并、备份、原子替换。
- YAML 拒绝 anchor/alias/merge key；JSON Schema 拒绝未知字段和越界值。
- 新增 9 个单元测试。

## 影响

- 配置以文件为唯一事实；secret 不进入普通 YAML。
- LKG 与备份位于 `state/`，用户不直接编辑。
- 迁移器与审计数据库尚未实现。