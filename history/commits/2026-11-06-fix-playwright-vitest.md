---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - web
docs_impact: false
docs_reason: 仅修正测试文件匹配规则，测试命令与文档描述未变化
wiki_impact: false
wiki_reason: 用户操作与教程未变化
breaking: false
tests: npm test; npx playwright test --list; npm run typecheck; npm run build; agent-gate --staged
---

# 修复 Playwright 与 Vitest 测试文件冲突

## 背景

`web` workflow 中 Vitest 默认匹配 `*.spec.ts`，把 Playwright 的 `smoke.spec.ts` 也当成自己的测试执行，报 `Playwright Test did not expect test() to be called here`。

## 改动

- Playwright 文件重命名为 `smoke.e2e.ts`，避免被 Vitest 默认匹配。
- `playwright.config.ts` 增加 `testMatch: "**/*.e2e.ts"`。

## 影响

- `npm test` 只运行 Vitest 队列测试。
- `npm run test:e2e` 只运行 Playwright。

## 验证

- `npm test`：1 file / 4 tests passed。
- `npx playwright test --list`：列出 3 个 E2E。
- typecheck/build 通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
