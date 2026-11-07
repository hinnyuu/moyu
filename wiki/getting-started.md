# 入门

当前 `main` 已有可运行的 v0.0.1 阶段实现。本文解释项目要做什么、运行时长什么样，以及从哪读起。

## 一句话

moyu 把已经完成但还没提交的渲染文件重新打包成交付 ZIP：调整 ZIP 内部的修改时间（DOS mtime），并改写文件内部记录的渲染时间；源文件不动。解压 ZIP 会产生新的 inode，因此 ctime/btime 自然变成解压时刻。

## 你会得到什么

- 一个交付 ZIP；
- ZIP 条目时间是目标时间，最新文件接近你执行打包的时刻；
- 文件内部常见时间元数据被改写；
- 可以证明“只有元数据字节变化，像素/媒体流没有变”。

## 运行时长什么样

一个镜像，一个 Podman pod，多容器：

```text
Pod: moyu
├─ gateway   # 可选：项目自己终止 TLS 时启用
├─ api       # HTTP API、Web 静态文件、当前内置图片预览
├─ worker    # 打包任务
├─ preview   # 图片/视频/EXR 预览服务
└─ tusd      # 大文件断点续传
```

- 有外部 Caddy：不启动 gateway，由 Caddy 负责 TLS 和公网端口。
- 没有 Caddy：启动 gateway，挂载证书，支持热重载和双栈。
- 不用 Docker Compose；用 Podman pod + Quadlet 或 `podman play kube`。

## 推荐阅读顺序

1. [媒体时间与 ZIP](concepts/media-time.md)：理解为什么只改 mtime 就够。
2. [镜像、容器与 Podman pod](concepts/image-container-pod.md)：理解一个镜像怎么跑多个容器。
3. [Podman 单 Pod 多容器](operations/podman-single-pod.md)：实际部署操作。
4. [HTTPS、端口与证书](operations/https-ports-certificates.md)：自定义端口、证书和热重载。
5. [配置与 WebUI](operations/configuration.md)：配置目录、WebUI 和缺失默认。

## 当前状态

- 核心打包链路、API、Web、gateway、deploy、wasm 核心已实现并有 CI。
- preview 与 tusd 已是独立容器；HLS 尚未实现。
- 尚未创建 v0.0.1 标签。