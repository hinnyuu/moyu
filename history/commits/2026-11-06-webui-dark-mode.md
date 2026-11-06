---
date: 2026-11-06
branch: draft/v0.0.1-architecture
commit: (included in this commit)
modules:
  - docs
  - web
docs_impact: true
wiki_impact: true
breaking: false
tests: documentation-only
---

# WebUI 暗色主题要求

## 背景

WebUI 可能在夜班、暗房、投屏和移动设备上使用。用户明确要求支持暗色主题。暗色不是装饰项，而是 v0.0.1 的正式验收要求。

## 改动

- `modules/web/docs/index.md` 增加主题与可访问性要求。
- `modules/web/wiki/index.md` 增加面向人类的主题说明。
- `modules/web/AGENTS.md` 增加主题/design tokens 规则。
- `docs/development/style-guide.md` 增加 WebUI 主题规范。
- `docs/development/testing.md` 增加亮/暗主题测试。
- 新增 `wiki/development/webui-style.md`。
- `wiki/index.md`、`wiki/README.md`、项目 history 索引增加入口。

## 决策

- 支持 `system` / `light` / `dark`。
- 默认跟随系统，手动选择持久化。
- 首屏无主题闪烁。
- 语义化 design tokens，组件不散落硬编码颜色。
- WCAG AA 对比度；焦点/错误/禁用态两套主题都清晰。
- 媒体预览不随主题反相，透明区域用中性棋盘格。
- Playwright 覆盖两套主题、切换持久化、首屏无闪烁。

## 影响

- v0.0.1 的 WebUI 验收必须包含暗色主题。
- 本提交只有文档，没有代码实现。

## 验证

- 文档链接检查。
- 模块 docs/history/wiki 结构检查。
- 无代码测试。

## 后续

- 实现阶段先建立 design tokens 和主题 bootstrap，再写页面组件。
- 每个新组件提交亮/暗截图或视觉回归基线。