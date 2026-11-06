# 概念：媒体时间与 ZIP

## 1. 四种文件时间

Linux 文件常见四个时间：

| 时间 | 含义 | 谁能改 |
| --- | --- | --- |
| `atime` | 最后访问时间 | 用户可设，但读取可能再改 |
| `mtime` | 内容最后修改时间 | 用户可设，但写入会再改 |
| `ctime` | inode 状态变更时间 | 内核维护，用户不能直接设 |
| `btime` | 创建时间 | 文件系统创建 inode 时决定，Linux 用户态不能改 |

`ctime` 不是创建时间，而是 change time。`touch` 改 mtime/atime 时，内核会把 ctime 设为当前时间。

## 2. ZIP 只携带 mtime

传统 ZIP 的本地头和中央目录只有一组 DOS 时间：

- 精度 2 秒；
- 没有时区，按打包机器本地时间解释；
- 只有 mtime；
- Linux ctime 完全不保存；
- btime 只在可选扩展字段里，Linux 解压通常无法恢复。

所以把文件放进 ZIP，再解压，会得到：

- mtime = ZIP 里的值；
- ctime/btime = 解压时刻；
- atime = 解压工具决定。

这正是项目以 ZIP 为核心的原因：ZIP 是“时间戳载体”，解压会重置内核维护的时间。

## 3. 文件内部还有时间

除了文件系统时间，媒体文件内部也可能记录渲染时间：

- EXR header `Date`；
- PNG `tEXt`/`eXIf`；
- JPEG COM/EXIF/XMP；
- TIFF EXIF/XMP；
- AVIF/WebP EXIF/XMP；
- MP4/MOV `©day`、`mvhd/tkhd/mdhd`；
- MKV `DATE` 标签、`DateUTC`。

moyu 默认在写入 ZIP 时改写这些字段，源文件不动。

## 4. 为什么不能只改文件系统时间

老板如果解压 ZIP 后只用文件管理器看，mtime 足够；但只要用能读元数据的工具查看 EXR/PNG/MP4，内部日期仍会暴露真实完成时间。因此需要两层：

1. ZIP 条目 DOS mtime；
2. 文件内部时间元数据。

## 5. 精度与限制

- DOS mtime 只有 2 秒精度；
- 跨时区解压可能显示偏移；
- 内部元数据补丁要求等长或重建容器结构；
- 客户端 WASM ZIP 在 v0.0.1 只承诺 DOS mtime，不承诺内部元数据改写；
- 需要严格保证时使用服务端默认路径。详细支持列表见 `docs/architecture/overview.md` 和 `modules/media-metadata/`。