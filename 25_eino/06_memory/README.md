# 记忆与对话上下文管理

> 源码: `/Users/songxijun/workspace/otherProject/eino/adk/middlewares/`、`/Users/songxijun/workspace/otherProject/eino/adk/filesystem/`
> 记忆是 ADK 层对话管理的核心能力——管理多轮对话历史，解决上下文窗口溢出问题。

## 一、概述

在多轮对话 Agent 中，**记忆**负责持久化和裁剪对话历史：

- **持久化**: 对话跨进程/跨轮次保存，用户回来可以继续对话
- **上下文裁剪**: LLM 上下文窗口有限，对话长了需要裁剪（滑动窗口、摘要压缩），避免溢出
- **可检索**: 可以从历史中检索相关内容注入当前上下文

Eino ADK 层把记忆设计成 **Backend + Middleware** 组合：

- **Backend**: 存储对话历史，支持 `InMemory` / `FileSystem` 等
- **Middleware**: 放到 ChatModelAgent 的中间件链上，在每次模型调用前**裁剪对话历史**，保证不超出窗口

## 二、文档索引

| 文档 | 内容 | 状态 |
|------|------|------|
| [`README.md`](./README.md) | 总览:记忆概念、架构 | ✅ |
| [`memory.md`](./memory.md) | 核心概念:对话历史、上下文窗口、裁剪策略 | ✅ |
| [`backend.md`](./backend.md) | Backend 接口、内置实现(InMemory / FileSystem) | ✅ |
| [`middlewares.md`](./middlewares.md) | 内置中间件:滑动窗口、摘要压缩 | ✅ |
| [`examples.md`](./examples.md) | 完整使用示例 | ✅ |

## 三、架构

```
┌─────────────────────────────────────────────────────────────┐
│ ChatModelAgent                                            │
│   ┌───────────────────────────────────────────────────────┐   │
│   │  Middleware chain                                     │   │
│   │   → Memory middleware (compress history)                │   │
│   │   → Next middleware                                  │   │
│   └───────────────────────────────────────────────────────┘   │
│                                       │                   │
│   Get history from Backend → 裁剪 → 喂给模型             │
└─────────────────────────────────────────────────────────────┘
```

- Backend: 存储完整对话历史
- Memory Middleware: 从 Backend 读历史，裁剪成不超过上下文窗口大小，传给模型

## 四、参考

- ADK 层总览放在 [../07_adk/](../07_adk/)
- 本机源码: `/Users/songxijun/workspace/otherProject/eino/adk`
