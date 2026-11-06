---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - media-metadata
docs_impact: false
docs_reason: 仅修正测试对不可访问素材路径的判断，模块行为与文档描述未变化
wiki_impact: false
wiki_reason: 使用方式与排错流程未变化
breaking: false
tests: python3 -m unittest discover -s modules/media-metadata/tests -v; agent-gate --staged
---

# 修复 media-metadata 测试在 CI 的素材探测

## 背景

GitHub Actions 的 Python workflow 在导入 `test_media_metadata.py` 时失败：模块级
`skipUnless` 直接对 `/root/.local/...` 调用 `Path.exists()`，在 runner 上抛出
`PermissionError`，导致整个测试模块加载失败，而不是按预期跳过。

## 改动

- 新增 `available(path)` 辅助函数，捕获 `OSError` 并返回 `False`。
- `image_files()` 与视频素材的 `skipUnless` 改用 `available`。

## 影响

- 素材不存在或不可访问时，相关用例正常跳过。
- 合成用例与本地素材用例行为不变。

## 验证

- `python3 -m unittest discover -s modules/media-metadata/tests -v`：8 passed。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
- 待 GitHub `python` workflow 确认。