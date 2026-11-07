---
date: 2026-11-06
module: deploy
commit: (included in this commit)
---

# 修复 tusd 构建路径

## 改动

- 使用 `find` 定位发布包内的 tusd 二进制，再 install。

## 影响

- 构建兼容 tusd 压缩包的不同目录布局。
