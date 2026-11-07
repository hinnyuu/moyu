---
date: 2026-11-06
branch: main
commit: (included in this commit)
modules:
  - deploy
docs_impact: true
wiki_impact: true
breaking: false
tests: python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"; agent-gate --staged
---

# GHCR 发布与供应链报告

## 背景

发布前审计要求镜像发布、SBOM、漏洞扫描与升级/回滚说明；此前只有 podman smoke，没有发布流程。

## 改动

- 新增 `.github/workflows/release.yml`：
  - `v*` 标签触发；
  - Podman 构建并推送 GHCR `:<tag>`、`:sha-<12位>`、`:latest`；
  - Syft 生成 SPDX SBOM；
  - Trivy 生成表格与 SARIF 报告；
  - SBOM/报告附加到 GitHub Release。
- 新增 `wiki/operations/upgrade-rollback.md` 并从 wiki 索引链接。
- deploy docs 增加发布章节；root README 更新状态。

## 影响

- 首次 `v0.0.1` 标签会真正执行发布；在此之前没有实际推送 GHCR。
- 仅 amd64 构建；未实现镜像签名。
- Trivy 当前不阻断发布，只产出报告。

## 验证

- release workflow YAML 解析通过。
- `python3 modules/agent-gate/src/agent_gate.py check --staged`。
- 待打标签后验证 GHCR、SBOM 与扫描报告。
