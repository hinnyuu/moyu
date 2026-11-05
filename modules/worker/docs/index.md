# worker 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

后台打包任务：拉取 job、执行 pipeline、更新进度、取消、恢复。

独立容器；轮询 SQLite/任务队列；执行 pipeline；进度/阶段/错误写回；取消检查；重启恢复；不与 API 合并。

## 非职责

不提供公网 HTTP、不处理上传、不做预览。

## 依赖

pipeline, storage, config

## 接口

JobStore、PackPlan、ArchiveWriter

## 失败模式

任务卡死、源文件变化、磁盘满、取消、重启。

## 测试

任务状态机、取消、恢复、并发、资源限制、失败回滚。

## 替换点

单进程轮询 → 外部队列/多 worker。
