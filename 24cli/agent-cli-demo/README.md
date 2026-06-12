# Agent CLI Demo

一个最小闭环 demo，用来演示这条链路：

`Agent -> mp-admin-cli -> AUTH_REQUIRED -> mp-sso-cli login -> poll -> token cache -> mp-admin-cli success`

## 目录

- `server/`: Node mock server，提供 mock SSO 和受保护业务接口
- `cli/`: Go CLI，包含 `mp-sso-cli` 和 `mp-admin-cli`
- `.demo-data/`: 本地 token/config 缓存目录

## 能力范围

- `mp-sso-cli login --server URL`
- `mp-sso-cli status`
- `mp-sso-cli logout`
- `mp-admin-cli dashboard summary --server URL`

当前仅演示：

- 设备码登录
- 轮询换 token
- 本地 token cache
- 业务 CLI 在未登录和已登录两种状态下的稳定输出

当前不演示：

- 真实 SSO
- keychain / 加密存储
- 多用户隔离
- 飞书 hook
- 真实业务系统

## 环境要求

- Node.js 23+
- pnpm 10+
- Go 1.23+

## 启动 mock server

```bash
make run-server
```

默认监听 `http://127.0.0.1:8787`。

## 构建 CLI

```bash
make build
```

## 演示闭环

一键跑完整个闭环：

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/24cli/agent-cli-demo
make demo
```

如果你想手动一步步跑，再执行下面这些命令。

先把 demo 本地数据收敛到项目目录：

```bash
export AGENT_CLI_DEMO_HOME="$PWD/.demo-data"
```

1. 未登录直接访问业务命令：

```bash
./bin/mp-admin-cli dashboard summary --server http://127.0.0.1:8787
```

预期返回：

```json
{
  "error": "AUTH_REQUIRED",
  "message": "please run mp-sso-cli login"
}
```

2. 执行登录：

```bash
./bin/mp-sso-cli login --server http://127.0.0.1:8787
```

命令会在 `stderr` 打印一个链接，例如：

```text
http://127.0.0.1:8787/mock/approve?user_code=USER_...
```

在浏览器打开这个链接，页面会直接把当前 `user_code` 标记为已授权。CLI 轮询成功后会输出：

```json
{
  "status": "ok",
  "logged_in": true,
  "server": "http://127.0.0.1:8787",
  "user": {
    "id": "demo-user",
    "name": "Demo User"
  },
  "token_cached": true
}
```

3. 再次调用业务命令：

```bash
./bin/mp-admin-cli dashboard summary
```

预期返回：

```json
{
  "summary": {
    "pending_reviews": 3,
    "published_items": 12,
    "today_visits": 248
  }
}
```

4. 查看登录状态：

```bash
./bin/mp-sso-cli status
```

5. 清理 token：

```bash
./bin/mp-sso-cli logout
```

## 测试

```bash
make test
```
