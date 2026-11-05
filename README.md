# moyu

实验性项目：把已经完成、但还没提交的渲染序列“重新出炉”。

当前处于尝试阶段，不设版本号；等路线完全稳定后再重构一次项目，从 `v0.0.1` 重新开始。

目前有两条路径：

- `moyu.sh`：直接平移源文件的 atime / mtime，适合需要让本机文件也看起来新鲜的场景。
- `moyu-pack` / `moyu-verify`：生成只记录 DOS mtime 的交付 ZIP，不修改源文件；解压后 ctime / btime 会自然变成解压时刻。

## 交付 ZIP（当前主线）

```bash
./moyu-pack -o delivery.zip /path/to/renders
./moyu-verify delivery.zip
```

`moyu-pack` 会：

1. 读取所有源文件的 mtime，保持它们之间的相对先后和间隔。
2. 把最新文件的 mtime 对齐到当前时刻（或 `--target` 指定的时间）。
3. 直接写 ZIP 条目的 DOS mtime，精度 2 秒。
4. 不修改源文件。
5. 默认改写文件内部时间元数据（EXR Date、PNG/JPEG/TIFF 时间字段、MP4/MOV `©day`、MKV DATE/DateUTC 等）。
6. 写完先校验，再原子改名为目标 ZIP。

先预览、不写文件：

```bash
./moyu-pack -o delivery.zip --dry-run /path/to/renders
```

逐文件查看源 mtime 到目标 mtime 的映射：

```bash
./moyu-pack -o delivery.zip -v /path/to/renders
```

同时生成时间清单，便于之后校验：

```bash
./moyu-pack -o delivery.zip --manifest delivery.json /path/to/renders
./moyu-verify --manifest delivery.json delivery.zip
```

指定目标时间：

```bash
./moyu-pack -o delivery.zip --target "2026-11-05 22:00:00" /path/to/renders
```

### 常用选项

| 选项 | 说明 |
| --- | --- |
| `-o, --output` | 输出 ZIP 路径 |
| `--target` | 最新文件目标时间，`now` 或 `YYYY-MM-DD HH:MM:SS` |
| `--tz` | 时区，默认 `Asia/Shanghai` |
| `--prefix` | ZIP 内统一前缀 |
| `--force` | 覆盖已存在的输出 |
| `--dry-run` | 只打印计划，不写 ZIP |
| `--deflate` | 使用 deflate 压缩（默认 STORE） |
| `--keep-metadata` | 保留文件内部元数据（默认改写） |
| `--chunk-size` | 读写块大小，默认 `1M` |
| `--manifest` | 输出 JSON 时间清单 |
| `--follow-symlinks` | 跟随符号链接 |
| `--no-fsync` | 写完不 fsync |
| `--json` | 输出 JSON 摘要 |
| `-v / -q` | 逐文件输出 / 只输出错误 |

### 默认行为

- 压缩：默认 `ZIP_STORED`，不压缩。渲染文件大多已经压缩过，deflate 收益低、CPU 开销高。
- 时区：默认 `Asia/Shanghai`，可用 `--tz` 覆盖。
- 目录：传入目录时，ZIP 内保留目录名作为顶层；目录内部的相对路径也保留。
- 符号链接：默认跳过；`--follow-symlinks` 可跟随。
- 覆盖：默认拒绝覆盖已有输出；`--force` 允许。
- ZIP64：大文件自动启用。
- 元数据：默认原地改写文件内部时间字段；`--keep-metadata` 可保留原样。
- 校验：打包后自动检查 extra field、DOS 时间、路径、加密、comment 等。

### 内部元数据改写

`moyu-pack` 默认直接修改写入 ZIP 的字节流，不修改源文件，也不重新编码像素或视频流。当前覆盖：

| 格式 | 改写字段 |
| --- | --- |
| EXR / Multi-Layer EXR | header 中的 `Date` 属性 |
| PNG | `tEXt` / 未压缩 `iTXt` 的日期字段；`eXIf` 中的 EXIF 日期；同步重算 chunk CRC |
| JPEG | `Blender:Date` COM 段、APP1 EXIF 日期、APP1 XMP 日期 |
| TIFF | EXIF `DateTime` / `DateTimeOriginal` / `DateTimeDigitized`、XMP、Photoshop IRB |
| WebP | `EXIF` chunk、`XMP ` chunk（如果存在） |
| AVIF | 通过 Pillow 定位 Exif 数据后改写其中的 EXIF 日期（如果存在） |
| MP4 / MOV | `©day` / `date` 字符串；非零的 `mvhd` / `tkhd` / `mdhd` creation/modification |
| MKV | `DATE*` 系列 TagString；`Info` 中的 `DateUTC` |

补丁全部要求**等长替换**，因此不会改变容器大小、媒体流偏移或像素数据。测试集里的 AVIF / WebP 没有可读日期字段，会保持原样。

压缩的 `zTXt` / `iTXt`、未知自定义元数据会继续打包并提示；无法生成等长补丁的时间字段会直接报错并停止打包。

### 校验器

`moyu-verify` 默认严格模式：除 ZIP64 `0x0001` 外，任何 extra field 都会失败，尤其是：

- `0x5455` UT（mtime / atime / creation time）
- `0x000a` NTFS（mtime / atime / creation time）
- `0x5855` UX
- `0x000d` PKWARE Unix

同时检查中央目录和本地文件头，避免只在其中一处藏时间字段。

```bash
./moyu-verify --require-store delivery.zip
./moyu-verify --check-crc delivery.zip
./moyu-verify --no-future delivery.zip
./moyu-verify --json delivery.zip
```

`moyu-verify` 只校验 ZIP 结构和 DOS 时间；内部元数据改写结果记录在 `--manifest` 的 `metadata` 字段里，可以用它逐文件复查。

### 沙箱性能基线

低配沙箱（2 核、7.8GB 内存、overlayfs）实测，均使用 `--no-fsync`，避免沙箱 fsync 抖动：

| 场景 | 方案 | 墙钟 | 峰值 RSS | 有效吞吐 |
| --- | --- | --- | --- | --- |
| 512MiB 单文件 | Python STORE，1M 块 | 1.9s | 约 20MB | 约 267MiB/s |
| 512MiB 单文件 | `zip -0 -X` | 3.4s | 约 10MB | 约 151MiB/s |
| 512MiB 单文件 | `dd` 复制基线 | 0.8s | 约 10MB | 约 621MiB/s |
| 2000 × 128KiB | Python STORE，1M 块 | 1.2s | 约 19MB | 约 204MiB/s |
| 2000 × 128KiB | `zip -0 -X` | 2.5s | 约 10MB | 约 99MiB/s |
| 4.3GiB 单文件 | Python STORE + ZIP64 | 18.0s | — | 约 240MiB/s |

这些数字只代表当前沙箱，NAS 上需要重新测；但可以看出 Python STORE 并不是性能瓶颈，反而比 `zip -0 -X` 更快，内存占用也很低。

### Docker / NAS 注意事项

- 容器里必须显式设置时区，否则默认 UTC 会产生 8 小时偏移：

  ```bash
  docker run --rm -e TZ=Asia/Shanghai -v /data:/data image ...
  ```

- 建议限制资源，避免打包抢占 NAS 和渲染机资源：

  ```bash
  docker run --rm \
    --cpus 1 --memory 512m --pids-limit 128 \
    --blkio-weight 300 --network none \
    -e TZ=Asia/Shanghai -v /data:/data image ...
  ```

- 宿主机上可用 `nice` / `ionice` 降低优先级。
- 打包需要与源文件等量的临时空间，因为默认 STORE；`moyu-pack` 会先检查可用空间。
- 输出先写 `.part`，校验通过后再原子改名；中断不会留下半个目标 ZIP。

### 当前限制

- DOS 时间只有 2 秒精度，小于 2 秒的帧间隔会被压平。
- DOS 时间没有时区信息；跨时区解压会按解压机本地时间解释。
- 不写入目录条目；解压时目录由解压工具创建。
- 内部元数据改写只覆盖上面表格中的字段；压缩元数据、未知自定义字段、非时间字段（File / Software / Camera 等）不改。
- 等长补丁是硬约束；如果某个时间字段无法等长替换，会报错并停止打包。
- AVIF Exif 改写依赖 Pillow；未安装时会跳过并提示。
- 打包本身会读取源文件，可能更新源文件 atime；不改 mtime / ctime / btime。
- 源文件的时间保持不变；如果老板能直接看源机器，仍然能看到真实 mtime。

## moyu.sh

```bash
./moyu.sh /path/to/render/*.exr
./moyu.sh -n /path/to/render/*.exr
./moyu.sh -v /path/to/render/*.exr
```

它把一组文件的 atime / mtime 整体向后平移，保持相对先后，并让最新文件落在当前时刻。atime 平移后会被限制为不超过执行时刻。

选项：

| 选项 | 说明 |
| --- | --- |
| `-n, --dry-run` | 只显示将要执行的时间调整，不修改文件 |
| `-v, --verbose` | 显示每个文件调整前后的时间 |
| `-q, --quiet` | 不输出结果摘要 |
| `-h, --help` | 显示帮助 |
| `-V, --version` | 显示当前开发标识 |

限制：

- 只调整 atime / mtime；ctime 会被内核更新为执行时刻，btime 无法修改。
- `moyu.sh` 不处理文件内部元数据；交付 ZIP 路径请用 `moyu-pack`。
- 不递归目录，请用 shell 通配符展开文件。
- 依赖 GNU coreutils 的 `stat`、`touch`、`date`。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

## Roadmap

- [x] 实验性 ZIP 打包与校验原型
- [x] 常见图片/视频内部时间元数据改写
- [ ] 压缩元数据与更完整的 AVIF / WebP 覆盖
- [ ] ZIP 写入性能与资源限制调优
- [ ] Docker 中心化部署
- [ ] WebUI 操作
- [ ] 定时通过 SFTP / FTP 投递
- [ ] 路线稳定后重构，并从 v0.0.1 开始版本管理

## License

MIT