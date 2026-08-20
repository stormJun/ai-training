# Agent CLI Demo 参考

## 背景

这篇文档讨论的是：如果要按照“Agent 调用公司内部业务 CLI”的思路做一个 demo，可以参考哪些 GitHub 项目，以及一个最小可行的 CLI 方案应该长什么样。

这里说的 CLI 不是替代 HTTP。实际链路通常是：

```text
Agent -> 业务 CLI -> 内部 HTTP API -> 业务系统
```

也就是说，CLI 底层还是会调用 HTTP API，只是不把 HTTP 细节、Token、鉴权流程直接暴露给 Agent。

## 为什么用 CLI 包一层

直接让 Agent 调 HTTP 会带来几个问题：

- Token、Cookie、API Key 容易暴露在 Prompt、日志、请求参数或调试输出里。
- 内部系统接口数量很多，直接暴露 HTTP 等于给 Agent 一个过大的操作面。
- 每个系统的 Header、分页、错误码、返回结构可能都不一样，Agent 容易拼错请求。
- 权限和审计不好统一，难以确认每个请求对应的真实用户。
- HTTP 错误语义复杂，Agent 很难稳定处理 401、403、500 和业务错误码。

CLI 的作用是把这些复杂细节收口：

- 参数校验
- 鉴权逻辑
- Token 获取
- HTTP 请求细节
- 返回格式
- 错误码
- 权限边界
- 审计信息

Agent 只需要调用稳定的命令，并读取结构化 JSON。

## GitHub 参考项目

### 普通业务 CLI 框架

- [fastapi/typer](https://github.com/fastapi/typer)
  - Python CLI 框架。
  - 适合快速写 demo。
  - 可以很快做出类似 `abtest-cli experiment get --id xxx --json` 的命令。

- [spf13/cobra](https://github.com/spf13/cobra)
  - Go 生态常用 CLI 框架。
  - 适合写更正式的公司内部 CLI。

- [spf13/cobra-cli](https://github.com/spf13/cobra-cli)
  - Cobra 的命令生成器。
  - 可以快速 scaffold CLI 项目结构。

### 带登录 / SSO / OAuth 思路的 CLI

- [FusionAuth/fusionauth-example-go-device-code-grant](https://github.com/FusionAuth/fusionauth-example-go-device-code-grant)
  - 比较接近 `sso-cli` 的思路。
  - CLI 触发登录，用户在浏览器完成授权，CLI 再拿 token。

- [cli/cli](https://github.com/cli/cli)
  - GitHub 官方 CLI，也就是 `gh`。
  - `gh auth login` 是生产级登录 CLI 的参考。
  - 它会通过浏览器登录，并把 token 存到系统 credential store。
  - 官方文档：[gh auth login](https://cli.github.com/manual/gh_auth_login)

- [clelange/cern-sso-cli](https://github.com/clelange/cern-sso-cli)
  - 一个直接叫 SSO CLI 的例子。
  - 支持 token、device、status、JSON 输出等子命令。
  - 适合参考 SSO CLI 的命令结构。

### Agent 友好型 CLI

- [basnijholt/agent-cli](https://github.com/basnijholt/agent-cli/)
  - 面向 AI / Agent 的本地 CLI 工具集。
  - 可以参考它的 JSON 输出和工具调用设计。

## 最小 Demo 设计

推荐先做两个 CLI：

```text
sso-cli
abtest-cli
```

其中：

- `sso-cli` 负责登录、授权、Token 存储。
- `abtest-cli` 代表公司内部业务 CLI，负责查询 AB 实验。
- `abtest-cli` 不直接暴露 Token，只通过内部逻辑读取当前用户凭证。

### 查询业务数据

Agent 或用户执行：

```bash
abtest-cli experiment get --id exp_123 --json
```

如果已经登录，返回：

```json
{
  "id": "exp_123",
  "name": "首页推荐实验",
  "status": "running",
  "owner": "zhangsan"
}
```

### 未登录时的错误

如果当前用户没有登录，业务 CLI 返回固定错误：

```json
{
  "error": "AUTH_REQUIRED",
  "message": "please run sso-cli login"
}
```

退出码可以约定为非 0，例如：

```text
10 = AUTH_REQUIRED
```

这样 Agent 能稳定识别“需要先登录”，而不是猜测错误原因。

### 登录流程

用户或 Agent 执行：

```bash
sso-cli login
```

最小版本可以先用 OAuth device code / poll 模式：

```text
1. sso-cli 向 SSO 平台申请一次性 code 和登录链接。
2. 用户打开链接，在浏览器完成登录。
3. sso-cli 轮询 SSO 平台，用 code 换取 token。
4. sso-cli 把 token 加密存到本地。
5. Agent 再次调用 abtest-cli。
```

如果要贴近公司内部 IM 场景，可以把登录链接发送到飞书卡片里，让用户点击授权。

### 登录后重试

登录完成后再次执行：

```bash
abtest-cli experiment get --id exp_123 --json
```

这时 `abtest-cli` 内部流程是：

```text
1. 读取当前用户标识。
2. 读取本地加密 token。
3. 调内部 HTTP API。
4. 把 API 返回结果整理成稳定 JSON。
5. 输出给 Agent。
```

## 推荐命令规范

业务 CLI 尽量遵守以下约定：

- 所有面向 Agent 的命令都支持 `--json`。
- 成功结果只输出 JSON 到 stdout。
- 错误信息输出结构化 JSON。
- 日志、调试信息不要混在 stdout。
- 用稳定退出码区分错误类型。
- 不在输出、日志、异常中打印 Token。

示例错误：

```json
{
  "error": "PERMISSION_DENIED",
  "message": "current user has no permission to access this experiment"
}
```

示例退出码：

```text
0  = OK
10 = AUTH_REQUIRED
11 = PERMISSION_DENIED
12 = TOKEN_EXPIRED
20 = INVALID_ARGUMENT
50 = INTERNAL_ERROR
```

## 推荐技术路线

如果只是快速 demo：

```text
Python + Typer
```

如果要更接近生产环境：

```text
Go + Cobra
```

如果要模拟 SSO 登录：

```text
OAuth device code / poll 模式
```

如果要模拟安全存储：

```text
系统 Keychain / Credential Store + 本地加密文件
```

## 一句话总结

CLI 不是为了替代 HTTP，而是为了把企业内部 HTTP API 包装成 Agent 安全可控、输出稳定、可审计的工具接口。
