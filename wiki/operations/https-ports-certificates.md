# 操作：HTTPS、端口与证书

本文解释项目如何做到“端口可配置、证书可挂载、更新可热重载”，以及 external Caddy 与 standalone 两种模式的区别。

## 1. 端口不写死

端口来自配置：

```yaml
# config/modules/gateway.yaml
listen:
  ipv4: "0.0.0.0"
  ipv6: "::"
  port: <port>
```

- `<port>` 是占位符，不是固定值。
- 端口范围 1–65535；rootless Podman 绑定 <1024 需要额外能力。
- standalone 模式：gateway 监听配置端口。
- external Caddy 模式：公网端口由 Caddy 决定，项目只配置内部端口。

## 2. host 还是 bridge

### host network

- gateway 直接绑定配置端口，不需要 Podman `PublishPort`。
- 改端口 = 改配置 + 重启 gateway。
- 隔离性弱一些；端口冲突由宿主承担。
- IPv4/IPv6 由 gateway 直接监听。

### bridge

- 容器端口和宿主端口需要 `PublishPort` 对应。
- 改公网端口需要改 Quadlet/pod 配置并重建容器。
- WebUI 修改 `listen.port` 不会自动改宿主端口；UI 必须提示。

### 外部 Caddy

- 公网端口和 TLS 完全由 Caddy 管理。
- 项目内部端口只需 Caddy 可达。
- 不需要 gateway。

## 3. 证书挂载

目录结构：

```text
/certs/
├─ tls.crt     # leaf → intermediate 完整链
└─ tls.key     # 私钥
```

- 挂载**目录**，不要只挂单文件；原子替换/symlink 更新更可靠。
- 私钥只读，权限收紧。
- 启动加载失败必须退出，避免无证书运行。
- 证书链顺序 leaf 在前。

## 4. 热重载触发

默认：

- 启动加载；
- 每 30 秒轮询；
- 管理 API 立即触发。

可选：

- fsnotify 监听；
- SIGHUP。

不是三种全开，按配置勾选。外部证书更新程序写入目录后，轮询/API 会加载新证书。

## 5. 管理 API 与 token

内部 API：

```text
POST /admin/cert/reload
GET  /admin/cert/status
Authorization: Bearer <token>
```

默认只监听 Pod 内回环地址，不暴露公网。远程调用通过 SSH 隧道/VPN：

```bash
ssh -L <admin-port>:127.0.0.1:<admin-port> user@host
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:<admin-port>/admin/cert/reload
```

token：

- WebUI 生成/轮换/撤销/复制一次；
- 明文写入 `/config/secrets/gateway_reload_token`（0600）；
- gateway 每次请求读取，轮换立即生效；
- 当前不维护 token 数据库元数据；
- 不记录到日志。

## 6. 重载语义

- 只读取已挂载的证书文件，不接受 HTTP 上传证书/私钥。
- 校验证书链、私钥匹配、有效期。
- 成功原子切换；新握手使用新证书，旧连接不断。
- 失败保留旧证书并返回错误。
- 返回 `cert_loaded_at`、`cert_sha256`、`cert_serial`、`cert_not_after`、`reloads`。

## 7. 双栈

- gateway 监听 IPv4 和 IPv6。
- 外部 Caddy 模式由 Caddy 负责双栈。
- 测试：

```bash
curl -4 "https://host:${PORT}/"
curl -6 "https://host:${PORT}/"
```

- 检查防火墙/安全组；IPv6 需要 AAAA 记录。
- bridge 模式需要确认 Podman 端口发布对 IPv6 的支持；host network 更直接。

## 8. 安全

- TLS 最低 1.2，优先 1.3。
- 管理 API 不暴露公网主路径。
- token 使用常量时间比较；失败限速。
- 证书/私钥不进日志、不进普通配置。
- 外部 Caddy 与 standalone 不要同时占用同一公网端口。