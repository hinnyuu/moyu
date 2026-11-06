# api 模块（人类说明）

api 是浏览器和后台服务之间的 HTTP 入口。它负责登录、创建任务、查进度、读写配置和返回预览地址，但不亲自打包。

## 首次登录

部署时生成一个 bootstrap token 文件。第一次打开 WebUI：

1. 输入 bootstrap token；
2. 设置管理员密码；
3. 之后只用密码登录。

```bash
curl -c cookies.txt -X POST https://<host>/api/v1/auth/session \
  -H 'Content-Type: application/json' \
  -d '{"bootstrap_token":"<token>","password":"<password>"}'
```

## 写操作需要 CSRF

登录后读取 `/api/v1/auth/session`，把返回的 `csrf` 放到 `X-CSRF-Token` 头：

```bash
curl -b cookies.txt -X PUT https://<host>/api/v1/config/worker \
  -H 'Content-Type: application/json' \
  -H 'X-CSRF-Token: <csrf>' \
  -d '{"patch":{"concurrency":4},"revision":"<revision>"}'
```

## 开发模式上传

生产由 tusd 处理分片；同源部署或本地开发可以直接使用 API 的分片端点：

```bash
curl -b cookies.txt -X PATCH https://<host>/api/v1/uploads/<id>   -H 'Upload-Offset: 0'   -H 'Content-Type: application/offset+octet-stream'   -H 'X-CSRF-Token: <csrf>'   --data-binary @chunk.bin
```

响应 204，`Upload-Offset` 头是新偏移量；全部传完后调用 `/finish`。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- `modules/contracts/openapi/openapi.yaml`：HTTP 契约。