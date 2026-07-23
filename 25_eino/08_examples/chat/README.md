# 完整聊天客户端示例

这是一个完整的**交互式命令行聊天客户端**，基于 `ChatModelAgent` + `FileSystem` 记忆 + `SlidingWindow` 裁剪，完整可运行。

## 功能

- 支持多轮对话，对话持久化（进程退出再进来还能接着聊）
- 支持流式输出，逐块打印
- 支持修改配置（上下文窗口大小、保留多少轮）
- 用火山方舟 Ark 模型，你改成 OpenAI 也很简单

## 使用

### 1. 配置环境

```bash
cd 08_examples/chat
cp .env.example .env
# 编辑 .env，填上你的 ARK_API_KEY，ARK_BASE_URL，ARK_MODEL
```

### 2. 运行

```bash
go run .
```

然后就可以开始聊天了，输入问题回车，模型流式输出。退出按 `Ctrl+C`。

## 代码结构

```go
// 核心流程
// 1. 加载环境
// 2. 创建后端
// 3. 创建记忆中间件
//  文件名就是 conversation ID（你也可以用用户 ID + 对话 ID）
// 4. 创建 ChatModelAgent
// 5. 创建 Runner
// 6. 进入循环：
//    - 读取用户输入
//    - 调用 agent.Query
//    - 流式打印输出
```

完整代码看 [`main.go`](./chat/main.go)，直接编译就能跑，依赖都在 `go.mod` 里。
