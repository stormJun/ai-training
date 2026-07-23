# ADK 智能体开发套件

> 源码: `/Users/songxijun/workspace/otherProject/eino/adk/`
> ADK 是 Eino 最上层的**智能体开发套件**，它把组件、编排、回调、记忆都组装起来，给你开箱即用的智能体。

## 一、概述

Eino 分层架构:

```
┌──────────────────────────────────────────────────────────────────┐
│  ADK (Agent Development Kit)    ← 最上层，开箱即用智能体        │
│  ────────────────────────────                            │
│  Compose (编排层)             ← 图编排、Pregel 执行、中断恢复  │
│  ────────────────────────────                            │
│  Components (组件层)         ← 组件抽象接口               │
│  ────────────────────────────                            │
│  Schema (类型层)             ← 基础类型: Message / Stream      │
└──────────────────────────────────────────────────────────────────┘
```

ADK 在 compose 层之上，提供:
- **标准 Agent 接口** — 统一智能体抽象
- **Runner** — 事件迭代器运行模式，流式输出支持更好
- **中间件机制** — 横切关注点:记忆、工具搜索、重试
- **预置智能体** — 开箱即用: `ChatModelAgent` / `Plan-and-Execute` / `DeepAgent` / `Supervisor`

**为什么用 ADK**:
- 你不需要自己拼 Graph，预置智能体直接用
- 中间件机制方便扩展，插记忆、日志不用改核心逻辑
- 统一运行模式，流式输出天然支持
- 底层还是 Eino compose 编排，需要定制可以直接拿去改

## 二、文档索引

| 文档 | 内容 | 状态 |
|------|------|------|
| [`README.md`](./README.md) | 总览、分层架构、文档索引 | ✅ |
| [`agent_interface.md`](./agent_interface.md) | Agent 接口、Runner 事件迭代、设计思想 | ✅ |
| [`chatmodel_agent.md`](./chatmodel_agent.md) | ChatModelAgent:开箱即用 ReAct 智能体、配置说明 | ✅ |
| [`middlewares.md`](./middlewares.md) | 中间件机制、内置中间件用法 | ✅ |
| [`prebuilt.md`](./prebuilt.md) | 预置智能体: PlanExecute / DeepAgent / Supervisor | ✅ |
| [`hitl.md`](./hitl.md) | 人机交互 HITL:中断恢复审批 | ✅ |
| [`examples.md`](./examples.md) | 完整可运行示例 | ✅ |

## 三、核心设计思想

ADK 的核心设计思想:
1. **Agent 就是一个带状态的流处理器** — Agent 接收输入，产出事件流（流式输出给客户端）
2. **组合大于继承** — 用中间件加功能，不要继承改代码
3. **底层依赖编排** — 所有 Agent 底层都是 compose Graph，能嵌能套，Agent 可以当工具用
4. **约定大于配置** — 默认配置满足绝大多数场景，需要改再改

## 四、参考

- 编排层: [../03_graph/](../03_graph/)
- 组件层: [../02_components/](../02_components/)
- 记忆: [../06_memory/](../06_memory/)
- 本机源码: `/Users/songxijun/workspace/otherProject/eino/adk`
