# pipeline 模块文档

状态：v0.0.1 架构草稿，尚未实现。

## 职责

打包业务编排：扫描/资产输入、时间计划、媒体补丁、ZIP 写入、manifest、校验。

串联 core-time、media-metadata、archive-zip；不依赖 Web、数据库或 HTTP。输入可以是文件/资产列表和 PackPlan；输出 ZIP + manifest + 校验结果。

## 非职责

不提供 HTTP、不管理用户、不调度浏览器、不直接持久化任务状态。

## 依赖

contracts, core-time, media-metadata, archive-zip

## 接口

PackPlan、ArchiveWriter、MetadataAdapter

## 失败模式

源文件变化、元数据改写失败、归档校验失败、manifest 写入失败。

## 测试

端到端打包、源文件不变、manifest 与 ZIP 一致、失败回滚。

## 替换点

编排逻辑与具体 adapter/writer 解耦，通过 contracts 装配。
