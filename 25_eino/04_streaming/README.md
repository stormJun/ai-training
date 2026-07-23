# 流式传输专题

> 本文档对应源码: `/Users/songxijun/workspace/otherProject/eino/schema/`、`/Users/songxijun/workspace/otherProject/eino/compose/`
> 底层设计深读见 [source_notes/stream_design.md](../source_notes/stream_design.md)，本文聚焦**用户层面用法**。

## 一、概述

Eino 把**流式**做成了贯穿全栈的一等公民：

- 组件层: 每个生成式组件(ChatModel 等)都同时提供 `Generate`(阻塞)和 `Stream`(流式)两个方法
- 编排层: 自动处理跨节点的流式衔接(拼接、装箱、合并、复制)，用户不需要自己手写 channel 循环
- ADK 层: Runner 返回事件迭代器，流式输出到客户端

核心抽象就是 `schema.StreamReader[T]` / `schema.StreamWriter[T]`，这套抽象贯穿组件、编排、ADK 三层。

## 二、文档索引

| 文档 | 内容 | 状态 |
|------|------|------|
| [`stream_api.md`](./stream_api.md) | StreamReader / StreamReader 基础 API、Pipe 创建、基本用法 | ✅ |
| [`convert_merge_copy.md`](./convert_merge_copy.md) | Convert 类型转换、Merge 多路合并、Copy 扇出 | ✅ |
| [`autopilot.md`](./autopilot.md) | 编排层自动流式衔接:节点间自动拼接/装箱/合并/复制 | ✅ |

## 三、核心思想

为什么 Eino 要把流式做这么深？

- **用户体验**: LLM 生成是渐进的，流式输出让用户更早看到内容，体验更好
- **端到端衔接**: 从模型输出 -> 编排节点 -> 客户端，全程可以保持流式，不需要等全部生成完
- **类型统一**: 不管底层是 channel、数组、多流合并，对外都是同一个 `StreamReader[T]` API，节点间不需要适配

要点:
- `StreamReader[T]` 是**单次消费**:每个 chunk 只能读一次
- **关闭必须**: `defer reader.Close()`，否则会 goroutine 泄漏
- 编排层**自动处理**:你只需要节点产出流，框架自动衔接下一个节点

## 四、参考

- 底层设计深读: [source_notes/stream_design.md](../source_notes/stream_design.md)
- 本机源码: `/Users/songxijun/workspace/otherProject/eino/schema/stream.go`
