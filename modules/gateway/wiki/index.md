# gateway 模块（人类说明）

gateway 是项目自己的 HTTPS 门卫。没有 Caddy 时它负责证书和端口；有 Caddy 时它可以休息。

## 什么时候会用到

standalone 部署需要 TLS 时启用 gateway；external Caddy 模式下不启动它。

## 运行

```bash
MOYU_GATEWAY_CONFIG=/config/modules/gateway.yaml moyu-gateway
```

配置里写清监听地址、证书文件、上游 API 地址和管理 API token 文件。

## 换证书

把新证书/私钥写到挂载目录，然后任选一种：

```bash
# 管理 API
curl -X POST -H "Authorization: Bearer <token>" \
  http://127.0.0.1:<admin-port>/reload

# 或轮询/ SIGHUP（若配置启用）
kill -HUP <gateway-pid>
```

无需重启容器，新连接会使用新证书。

## 相关

- [模块 docs](../docs/index.md)：当前设计事实。
- [模块 history](../history/index.md)：本模块历史。
- 根 `docs/contracts/`：跨模块契约。