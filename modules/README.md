# 模块目录

每个模块是一个可替换单元，自带 docs/history/wiki。

## 模块清单

| 模块 | 职责 |
| --- | --- |
| [contracts](contracts/) | OpenAPI、JSON Schema、模块接口 |
| [core-time](core-time/) | 时间策略、时间换算、Rust core crate |
| [media-metadata](media-metadata/) | 格式识别与元数据改写 |
| [archive-zip](archive-zip/) | ZIP 写入与校验 |
| [pipeline](pipeline/) | 打包编排 |
| [config](config/) | 配置加载、校验、原子写入 |
| [storage](storage/) | 资产、任务、输出、预览缓存 |
| [uploads](uploads/) | tus 断点续传 |
| [preview](preview/) | 缩略图、代理视频/图片 |
| [api](api/) | HTTP API、认证、静态 Web |
| [worker](worker/) | 后台打包任务 |
| [web](web/) | React 静态 SPA |
| [wasm-client](wasm-client/) | 可选浏览器 ZIP/预览 |
| [gateway](gateway/) | Rust TLS/反代/证书热重载 |
| [deploy](deploy/) | Podman/Quadlet/GHCR |
| [agent-gate](agent-gate/) | 文档/history/wiki 门禁 |

## 模块骨架

```text
modules/<name>/
├─ module.yaml
├─ README.md
├─ AGENTS.md
├─ docs/index.md
├─ history/index.md
└─ wiki/index.md
```

实现开始后再增加 `src/`、`tests/`。

## 模板

见 [模板](_template/)。新模块直接复制模板并改 `module.yaml`、docs、wiki。