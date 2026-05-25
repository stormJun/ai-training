# Memory 问答整理

这份文档整理了关于 Agent Memory 和 OpenClaw Memory 设计的一组问答，适合复习、面试表达和源码对照阅读。

## 1. 07_agent_memory_and_advanced_capabilities 主要讲什么

这个主题核心在讲两件事：

- Agent Memory 怎么设计
- 除了 Memory 之外，Agent 还能具备哪些高级能力

从目录内容看，重点明显偏向 Memory，主要覆盖：

- 短期记忆：`InMemorySaver` / checkpointer 保存当前会话上下文
- 摘要记忆：长对话压缩，降低 token 成本
- 滑窗记忆：只保留最近一段上下文
- 向量记忆：把事实写入向量库并按语义召回
- 长期记忆：用 FAISS 做持久化语义记忆
- 结构化记忆：知识图谱三元组存储
- 时序记忆：Redis TTL 让记忆可过期
- 工程增强：工具重试、RPA 集成、小模型优化等

一句话总结：

这个目录主要是在讲“如何给 Agent 构建从短期到长期、从文本到结构化的记忆系统”，并顺带覆盖一些工程化增强能力。

## 2. 如果面试官问：如何设计一个 Agent

比较稳的回答方式是从六个层次讲：

- 目标：它要解决什么问题，成功标准是什么
- 状态：当前任务状态和上下文如何保存
- 能力：是否需要工具调用、RAG、Memory、外部系统访问
- 流程：理解、规划、执行、校验如何编排
- 约束：权限、安全、超时、重试、降级
- 评估：成功率、延迟、成本、工具调用效果

面试版表达：

“我设计 Agent 一般会按目标、状态、能力、流程、约束和评估六个层次来考虑。先定义业务目标和成功标准，再决定它是否需要工具调用、知识检索和记忆；然后设计状态管理，区分短期上下文和长期记忆；流程上把任务拆成理解、规划、执行、校验几个阶段，并用工作流或状态机控制；最后补齐安全、重试、降级和观测评估。大多数业务场景我会优先做单 Agent + workflow，只有在任务天然适合分工时才会拆多 Agent。” 

## 3. Memory 应该怎么设计

### 3.1 长短期记忆怎么分

面试里可以这样回答：

“我会把 Memory 拆成两层：短期会话记忆和长期用户记忆。短期记忆解决当前 session 的上下文连续性，长期记忆解决跨 session 的个性化和持续性信息保存。”

短期记忆一般保存：

- 当前对话消息
- 工具调用结果
- 当前任务状态
- 工作流节点执行进度

长期记忆一般保存：

- 用户偏好
- 稳定事实
- 长期目标
- 重要决策
- 可复用知识

### 3.2 存在哪里

短期记忆和长期记忆通常不会放在同一个地方。

短期记忆常见存储：

- 进程内内存
- Redis
- workflow/checkpointer 状态存储
- session transcript

长期记忆常见存储：

- 关系库：MySQL / Postgres
- 向量库：FAISS / pgvector / Milvus
- 图存储：知识图谱或图数据库
- 工作区文件：Markdown / JSON / Note files

面试版表达：

“短期记忆重低延迟和会话态，长期记忆重持久化和检索，所以通常分层存储。短期记忆放 session state，长期记忆按数据类型分别放关系库、向量库或图存储。”

### 3.3 Memory 设计的关键不是存，而是写入和检索

真正重要的是三个问题：

- 存什么
- 什么时候写入
- 什么时候取出

如果没有写入门控和检索治理，Memory 很容易被噪声污染。

## 4. OpenClaw 是怎么做 Memory 的

## 4.1 总体思路

OpenClaw 不是传统那种“单独建一套用户画像数据库”的设计，它更像两层结构：

- 短期记忆：`session transcript + 当前上下文 + compaction summary`
- 长期记忆：工作区里的 `MEMORY.md` / `memory/*.md`，再加语义检索索引

### 4.2 短期记忆

OpenClaw 的短期记忆核心是 session transcript。

它会持续记录：

- 用户消息
- assistant 回复
- tool call
- tool result
- 运行时事件
- compaction summary

当上下文太长时，它会：

- 按最近若干轮限制历史
- 对旧对话做 compaction
- 保留最近消息和压缩后的摘要

所以短期记忆不是简单的“只存在内存里的历史消息”，而是：

“持久化 transcript + 面向上下文窗口的裁剪/摘要机制”

### 4.3 长期记忆

OpenClaw 的长期记忆不是一张用户事实表，而是工作区文件。

它的核心载体是：

- `MEMORY.md`
- `memory/*.md`

设计方式：

- `MEMORY.md` 可以在正常 session 中直接参与上下文
- `memory/*.md` 不全量注入，通过 `memory_search` 和 `memory_get` 按需召回
- 这些 Markdown 文件会被切块、做 embedding、建立每个 agent 独立的索引

也就是说：

- 真正的 memory source of truth 是文件
- SQLite 更像检索索引，不是长期事实的主存储

### 4.4 session transcript 也能被当成记忆检索源

OpenClaw 支持把 session transcript 纳入 memory search，但这是可选能力，不是默认开启。

这时系统会：

- 读取 `sessions/*.jsonl`
- 抽取 user/assistant 文本
- 清洗和脱敏
- 加入语义索引

所以它不是典型的“用户画像记忆系统”，而是：

“workspace knowledge memory + optional session recall”

### 4.5 面试版回答

“OpenClaw 的 memory 设计可以概括成两层。短期记忆是 session context，本质上由会话 transcript、history limit 和 compaction summary 组成，用来保证上下文连续性并控制窗口大小；长期记忆则是工作区里的 `MEMORY.md` 和 `memory/*.md`，通过 `memory_search` / `memory_get` 按需召回。系统会为这些 Markdown 文件建立每个 agent 独立的 SQLite 语义索引，必要时也可以把 session transcript 作为额外检索源。所以它的长期记忆更像 workspace knowledge memory，而不是传统 CRM 式用户画像库。” 

## 5. transcript 是什么

`transcript` 可以理解成“会话逐字记录”或者“对话流水”。

它通常记录：

- 用户消息
- assistant 回复
- tool call
- tool result
- 系统事件
- compaction summary

一句话：

“Transcript 是 session 的持久化事件日志，记录这次对话过程中发生过什么。”

它和 `MEMORY.md` 的区别：

- transcript：原始过程记录，偏短期、偏运行态
- MEMORY.md：提炼后的长期知识，偏稳定、偏可复用

## 6. 为什么 OpenClaw 有时会串题

例子：

- 第一轮问“视频剪辑”
- 第二轮问“OpenClaw 原理”
- 结果被理解成“OpenClaw 做视频剪辑的原理”

这个问题通常不是长期记忆写错了，而是短期会话上下文过强。

主要原因有三个：

### 6.1 同一 session 的上下文连续

OpenClaw 默认会把同一个 DM 或主会话持续复用，所以第二句会被当成第一句的 follow-up，而不是全新问题。

### 6.2 compaction 会优先保留最近任务语义

它的摘要策略会尽量保留：

- active tasks
- the last thing the user requested
- what was being done about it

这样对连续任务有帮助，但对突然换话题不友好。

### 6.3 用户表达存在省略

“关于 OpenClaw 原理”如果没有明确说“换个话题”，模型会尝试把它补全到上一轮主题里。

一句话总结：

“这个问题主要不是 memory store 存错了，而是同一 session 下的短期上下文连续性太强，模型把第二问错误地当成了第一问的追问。”

## 7. OpenClaw 是怎么切换 session 的

OpenClaw 的 session 需要分成两层理解：

- `sessionKey`
- `sessionId`

### 7.1 sessionKey 是“会话线路”

它决定消息路由到哪一条会话线上。

典型例子：

- `agent:main:main`：主会话
- `agent:main:discord:channel:12345`：某个 Discord 频道
- `agent:main:direct:alice`：某个用户单独的 DM 会话

DM 是否共用主会话，取决于 `session.dmScope`：

- `main`
- `per-peer`
- `per-channel-peer`
- `per-account-channel-peer`

### 7.2 sessionId 是“这一段会话实例”

即使 `sessionKey` 不变，也可能重新开一段新的 session。

常见触发条件：

- `/new`
- `/reset`
- daily reset
- idle reset

所以可以这样理解：

- `sessionKey`：聊天窗口编号
- `sessionId`：这个窗口里当前这一轮会话编号

### 7.3 面试版表达

“OpenClaw 不是只有一个 session 概念，它把会话拆成 `sessionKey` 和 `sessionId` 两层。`sessionKey` 决定消息路由到哪条会话线，比如主会话、某个群组、某个用户；`sessionId` 决定这条会话线上当前是不是一段新的会话实例，所以 `/new` 或 `/reset` 通常不是换 routing key，而是在同一个 sessionKey 上重开一段新会话。” 

## 8. 一组适合面试的短回答

### 8.1 OpenClaw 是怎么做 Memory 的

“OpenClaw 的短期记忆主要由 session transcript、history limit 和 compaction summary 组成，用来保证上下文连续性并控制上下文窗口；长期记忆主要是工作区里的 `MEMORY.md` 和 `memory/*.md`，通过 `memory_search` / `memory_get` 按需召回。它会为这些 Markdown 文件建立 per-agent 的 SQLite 语义索引，因此长期记忆更像 workspace knowledge memory，而不是传统用户画像库。” 

### 8.2 transcript 是什么

“Transcript 就是会话日志，记录用户、Agent、工具之间整个交互过程。它更像运行时历史，不等于长期记忆。” 

### 8.3 为什么会串题

“通常不是长期记忆写错了，而是同一 session 的短期上下文连续性太强，模型把后一句错误地当成前一句的追问。” 

### 8.4 OpenClaw 怎么切 session

“OpenClaw 把 session 拆成 `sessionKey` 和 `sessionId`。前者负责路由和隔离，后者负责在同一条会话线上做重开、过期和重置管理。” 

## 9. 最终总结

如果从工程实现角度总结 OpenClaw 的 memory：

- 它不是“数据库优先”的 memory 设计
- 它是“workspace-first”的 memory 设计
- 短期记忆依赖 transcript 和 compaction
- 长期记忆依赖 Markdown 文件和语义检索
- session 管理通过 `sessionKey` 和 `sessionId` 分层完成

如果从面试角度总结：

OpenClaw 的价值不在于它把 Memory 做得特别“炫”，而在于它把 Memory 做得足够工程化、可控、可检索、可维护。
