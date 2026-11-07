---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - deploy
docs_impact: true
wiki_impact: false
wiki_reason: 发布架构变化属于发布流程，用户操作不变
breaking: false
tests: python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"; agent-gate --staged
---

# 多架构镜像发布

## 背景

发布清单要求 arm64 进入发布；此前 release 只构建/推送 amd64。

## 改动

- release workflow 拆为：
  - `build-amd64`（ubuntu-latest）；
  - `build-arm64`（ubuntu-24.04-arm）；
  - `publish` 汇总多架构 manifest。
- 推送架构 tag：`:<tag>-amd64`、`:<tag>-arm64`、`:sha-<12位>-<arch>`。
- manifest：`:<tag>`、`:sha-<12位>`、`:latest`。
- SBOM/Trivy/Release 附件仍在 publish 阶段。
- deploy docs/release checklist/发布说明更新。

## 影响

- arm64 进入 GHCR 多架构镜像；未实现镜像签名。
- release workflow 需要 arm64 runner 可用。

## 验证

- workflow YAML 解析通过。
- 本地无法执行 tag 发布；待 `v0.0.1` 标签验证。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
