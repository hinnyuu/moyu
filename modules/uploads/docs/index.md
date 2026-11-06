# uploads 模块文档

状态：v0.0.1 阶段 2 最小实现（Python）。

## 职责

tus 断点续传会话、偏移量、完成钩子、入库。

前端 tus-js-client；tusd 负责分片/偏移/断点；API 签发上传 token/批次；完成后校验并注册资产；会话 TTL、清理、最大文件大小、配额。

## 非职责

不解析媒体、不打包、不直接写数据库业务表、不提供 HTTP 路由。

## 依赖

contracts, storage

## 接口

Python 包位于 `src/moyu_uploads/`：

- `UploadSessionStore(storage, max_upload_bytes, session_ttl_seconds=86400)`
  - `create_session(metadata) -> UploadSession`
  - `get_session(id)` / `get_offset(id)`
  - `append_chunk(id, offset, data) -> new_offset`
  - `finish_session(id) -> Asset`
  - `cancel_session(id)`
  - `expire_sessions(ttl_seconds=None) -> int`
- `UploadSession`：id、filename、size、offset、status、media_type、created_at、updated_at。
- `UploadError`：`code` / `message` / `details`。

`metadata` 至少包含 `filename` 和 `size`，可选 `media_type`。

## 存储布局

```text
<dataRoot>/uploads/<session-id>/data
<dataRoot>/uploads/<session-id>/meta.json
```

偏移量和状态写入 storage 的 `upload_sessions` 表；`meta.json` 保存 filename / media_type / size。

## 语义

- 分片必须按偏移顺序到达；偏移不一致返回 `offset_mismatch`。
- 分片累计长度不能超过声明的 `size`。
- `finish` 只在 `offset == size` 时成功，随后把文件移动为资产并删除会话。
- 会话关闭、取消或完成后不能再追加。
- 过期清理删除会话目录与数据库行。

## 失败模式

偏移不匹配、分片超长、上传未完成、会话不存在/已关闭、超过上限、配额不足、磁盘写失败、资产登记失败。

## 测试

`tests/test_uploads.py` 覆盖：

- 完整上传 → 资产 sha256/内容/媒体类型；
- 偏移不一致、分片超长、未完成 finish；
- 最大大小与配额；
- 完成/取消后不能追加；
- 过期清理；
- 新实例继续断点上传；
- 非法大小。

运行：

```bash
python3 -m unittest discover -s modules/uploads/tests -v
```

## 替换点

tusd → 自研/其他协议；本地 FS → 对象存储。替换必须保持会话 ID、偏移、顺序、完成入库与清理语义。