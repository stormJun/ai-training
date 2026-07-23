# ChatModel 基本 Demo

一个可运行的 ChatModel 使用示例,通过火山方舟 Ark 接入真实 LLM,演示 `Generate`(阻塞)、`Stream`(流式)与函数式选项(`WithTemperature`)的最小用法。

## 配置

demo 启动时自动加载同目录 `.env`(不存在则忽略;不覆盖已设置的环境变量)。从模板创建并填入真实 Key:

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/26eino/02_components/demo
cp .env.example .env   # 然后编辑 .env 填入真实 Key
```

`.env` 内容(Agent Plan 配置):

```
ARK_API_KEY=ark-你的AgentPlan专属Key
ARK_MODEL_ID=ark-code-latest
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/plan/v3
```

> `.env` 已被根 `.gitignore` 忽略,不会提交。环境变量也可直接 `export` 到 shell(优先级高于 `.env`)。

## 运行

```bash
go run .
```

实测输出(真实生成):

```
>> 已加载 .env
=== Generate ===
Go（又称Golang）是谷歌推出的开源静态强类型编译型编程语言，以语法简洁、原生支持高并发、
编译与运行效率优异为核心特性，广泛应用于云原生、微服务、分布式系统等开发场景。

=== Stream ===
Go（又称Golang）是谷歌推出的开源静态强类型编译型编程语言，天生支持高效并发、语法简洁
易上手，广泛应用于云原生、微服务、分布式系统等开发场景。
```

Agent Plan 支持的模型(可直接按名调用,免开通):`ark-code-latest`、`doubao-seed-2.0-code/pro/lite`、`deepseek-v4-flash/pro`、`minimax-m3`、`glm-5.2`、`kimi-k2.7-code` 等。

## Agent Plan vs 普通 Ark

两者是**不同产品,Key 与端点都不通用,切勿混用**:

| | 普通 Ark | Agent Plan(本 demo 默认) |
|---|---|---|
| Base URL | `https://ark.cn-beijing.volces.com/api/v3` | `https://ark.cn-beijing.volces.com/api/plan/v3` |
| API Key | 普通 Ark 平台 Key | **Agent Plan 专属 Key**(单独获取) |
| 模型可用性 | 需逐个开通 | `ark-code-latest` 等可直接调用 |
| 用普通 Key 调 Agent Plan | - | 401 鉴权失败 |
| 用 Agent Plan Key 调普通 Ark | 401 鉴权失败 | - |

改用普通 Ark:删掉 `.env` 里的 `ARK_BASE_URL`,`ARK_MODEL_ID` 填接入点 ID(`ep-xxx`)或已开通的模型 ID(需先在「开通管理」页开通模型服务)。

诊断速查:
- **401 `API key ... invalid`** -> Key 与端点不匹配(如拿 Agent Plan Key 调普通 Ark 端点),或 Key 复制有误。
- **404 `model ... does not exist or you do not have access`** -> Key 鉴权通过,但模型名不对 / 普通 Ark 未开通该模型。

## 实现要点

`main.go` 从 `.env`(或环境变量)读取配置,直接构造 `ark.ChatModel`:

```go
_ = godotenv.Load()                       // 加载 .env

cfg := &ark.ChatModelConfig{
    APIKey: os.Getenv("ARK_API_KEY"),
    Model:  os.Getenv("ARK_MODEL_ID"),
}
if baseURL := os.Getenv("ARK_BASE_URL"); baseURL != "" {
    cfg.BaseURL = baseURL                 // Agent Plan 覆盖为 /api/plan/v3
}
chatModel, err := ark.NewChatModel(ctx, cfg)
```

随后 `Generate` / `Stream` / 选项 / reader 关闭的代码与具体实现无关--`ark.ChatModel` 满足 `model.BaseChatModel` 接口,换其他实现(OpenAI、Ollama 等)时这部分不变。

## 文件结构

| 文件 | 职责 |
|---|---|
| `main.go` | 使用方:加载 `.env`、构造 Ark 模型、调用 `Generate` / `Stream`、处理选项与 reader 关闭 |
| `.env` | 真实配置(含 Key,已 gitignore,不入库) |
| `.env.example` | 配置模板,可安全提交 |
| `go.mod` | 独立模块,`replace` 指向本机 eino 源码,免联网下载 |

## 安全提醒

- `.env` 含真实 Key,已被根 `.gitignore` 忽略,**切勿**手动 `git add -f` 提交。
- Key 若曾粘贴到聊天/日志,测完请在控制台轮换。

## 关于 go.mod 的 replace

```go.mod
replace github.com/cloudwego/eino => ../../../../eino
```

demo 位于 `ai-training/26eino/02_components/demo`,eino 源码位于 `otherProject/eino`,相对路径向上四级,直接使用本机 eino 源码。改用线上发布版则删除 `replace` 并 `go get github.com/cloudwego/eino@latest`。

## 相关文档

- [`../chat_model.md`](../chat_model.md) -- ChatModel 接口与机制详解
- [`../../source_notes/stream_design.md`](../../source_notes/stream_design.md) -- `StreamReader/Writer` 底层设计
- [火山方舟 Agent Plan 接入](https://www.volcengine.com/docs/82379/1399008)
