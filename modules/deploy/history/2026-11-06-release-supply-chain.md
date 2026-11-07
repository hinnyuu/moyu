---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# 发布与供应链

## 改动

- 新增 GHCR 发布 workflow（tag/sha/latest）。
- SBOM、Trivy 报告、Release 附件。
- docs 增加发布章节。

## 影响

- 镜像发布从手工变为标签触发；仅 amd64，未签名。
