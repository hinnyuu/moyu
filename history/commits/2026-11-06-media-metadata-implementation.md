---
date: 2026-11-06
branch: feat/phase1-core-time-rust-ci
commit: (included in this commit)
modules:
  - media-metadata
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -m unittest discover -s modules/media-metadata/tests -v; agent-gate --staged
---

# media-metadata 阶段 1 最小实现

## 背景

阶段 1 需要把已验证的媒体时间字段改写逻辑收进 `media-metadata` 模块，并让 pipeline 能通过稳定接口拿到补丁计划或 materialize 结果。

## 改动

- 新增 `modules/media-metadata/src/moyu_media_metadata/`：`core.py`、`adapters.py`、`__init__.py`。
- 每个格式注册一个 `Adapter`：EXR、PNG、JPEG、TIFF、WebP、AVIF、MP4、MOV、MKV。
- 公开 `detect_format`、`build_metadata_patches`、`apply_patches`、`iter_patched_chunks`、`materialize_metadata`。
- 新增 8 个模块级测试，测试不再依赖根目录 `moyu-pack` CLI。
- 更新 media-metadata 的 README、docs、wiki 和 `module.yaml`。

## 影响

- pipeline 可以直接调用本模块生成补丁或物化文件，不再依赖根目录原型脚本。
- 源文件始终只读；materialize 输出写到调用方指定目录。
- 根目录 `moyu_media.py` 继续保留为参考实现，未删除。
- 仍未实现 AVIF idat/多 extent 等扩展场景。

## 验证

- `python3 -m unittest discover -s modules/media-metadata/tests -v`：8 passed（素材存在时含图片/视频矩阵）。
- `python3 -m unittest discover -s modules/archive-zip/tests -v`：15 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。