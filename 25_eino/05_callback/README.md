# 回调与可观测性

> 源码:`/Users/songxijun/workspace/otherProject/eino/callbacks/`
> 本文是回调总览，阐述 Eino 固定切点切面 AOP 设计。

## 一、概述

Eino 采用**固定切点 AOP** 设计回调机制:在组件执行的关键生命周期点，框架自动调用你注册的回调处理器。你可以用回调实现:

- **日志**: 打印每个组件输入输出摘要
- **指标采集**: Token 计数、耗时统计、QPS 监控
- **链路追踪**: OpenTelemetry 链路追踪集成
- **调试**: 流式过程中打印每个 chunk
- **审计**: 记录所有 LLM 请求和响应

核心设计思想:**切点固定，处理器可插拔**。五个固定切点覆盖所有执行场景，组件实现者只需要在正确切点调用 `callbacks.OnStart` 等方法，用户只需要实现 `Handler` 接口处理关心的事件。

## 二、文档索引

| 文档 | 内容 | 状态 |
|------|------|------|
| [`README.md`](./README.md) | 总览、核心概念、设计思想 | ✅ |
| [`handler.md`](./handler.md) | Handler 接口、五个切点、NewHandlerBuilder 用法 | ✅ |
| [`inject.md`](./inject.md) | 切面注入机制:组件如何调用回调、上下文传递 | ✅ |
| [`examples.md`](./examples.md) | 常见使用示例:日志、Token 统计、链路追踪 | ✅ |

## 三、核心概念

### 3.1 五个切点

Eino 在组件执行的五个生命周期点提供回调入口:

| 切点 | 时机 | 输入 | 适用场景 |
|------|------|------|----------|
| `TimingOnStart` | 组件开始执行前 | 组件输入 | 日志输入、开始计时 |
| `TimingOnEnd` | 组件成功执行完后 | 组件输出 | 日志输出、记录耗时、Token 统计 |
| `TimingOnError` | 组件执行返回错误 | 错误 | 错误日志、错误计数 |
| `TimingOnStartWithStreamInput` | 组件输入是流式 | 输入流的 copy | 流式输入日志 |
| `TimingOnEndWithStreamOutput` | 组件输出是流式 | 输出流的 copy | 流式输出 token 统计 |

### 3.2 作用域

回调有三个作用域，优先级从高到低:

1. **调用时指定**: `compose.WithCallbacks(handlers...)` —— 单次 `Runnable.Invoke` / `Stream` 调用生效
2. **全局**: `callbacks.AppendGlobalHandlers` —— 进程内所有组件调用都生效
3. **编排中指定**: 给 Graph 中某个节点单独加回调 —— 很少用

优先级: 调用时指定 > 全局 > 编排节点指定

### 3.3 RunInfo 信息

每个回调都会收到 `*callbacks.RunInfo`，含:

```go
type RunInfo struct {
	Name      string          // 节点名/用户指定名
	Type      string          // 组件实现类型(如 "OpenAI")
	Component components.Component  // 组件类别(如 components.ComponentOfChatModel)
}
```

你可以根据 `Component` 判断是不是你关心的组件类型。

## 四、设计要点

- **不强制实现所有方法**: `TimingChecker.Needed` 告诉你框架哪些切点你实现了，没实现的跳过，不产生 overhead
- **流式必须 Copy**: 流式输入输出，框架自动给每个 Handler Copy 一份独立流，Handler 必须 Close 避免泄漏
- **上下文传递**: Handler OnStart 返回 context.Context，这个 context 会传给后面的 OnEnd/OnError，方便你把 start 的状态(比如开始时间)存在 context 里
- **顺序**: OnStart 逆注册顺序调用，OnEnd/OnError 正注册顺序调用，符合中间件约定

## 五、参考

- Handler 构建: [handler.md](./handler.md)
- 切面注入: [inject.md](./inject.md)
- 示例: [examples.md](./examples.md)
- 本机源码: `/Users/songxijun/workspace/otherProject/eino/callbacks`
