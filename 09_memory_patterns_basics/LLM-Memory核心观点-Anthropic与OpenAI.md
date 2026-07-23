# LLM Memory 核心观点与工程要点：Anthropic 与 OpenAI

## Anthropic：Context Management 核心三点

来源文章：<https://claude.com/blog/context-management>

### 核心一：Memory 不是保存全部历史

Anthropic 的关键观点是，长任务里真正有价值的并不是完整聊天记录或全部工具输出，而是少量关键状态，例如：

- 当前任务进度
- 关键阶段结论
- 用户偏好
- 重要决策与约束

也就是说，`memory` 的目标不是“记住一切”，而是“保留后续推理真正需要的信息”。

### 核心二：上下文管理和长期记忆要分开做

Anthropic 把这件事拆成两个独立能力：

- `context editing`：清理当前上下文窗口中已经过时的 tool outputs
- `memory tool`：把重要信息写入上下文窗口之外的持久层

这背后的工程思想很直接：

- 该删的删
- 该存的存
- 不要把所有历史都持续塞进 prompt

### 核心三：长程 Agent 的瓶颈往往是 Context Hygiene

很多 Agent 在长任务中表现变差，不一定是模型能力不足，而是上下文变脏了。比如：

- 旧搜索结果还留在上下文里
- 旧文件内容和旧日志不断累积
- 已经消费过的中间结果没有被清理

这些内容会带来三个问题：

- 成本更高
- 延迟更大
- 推理更容易被无关信息干扰

更好的方式是：

1. 先把关键结论提炼出来
2. 写入长期 memory
3. 清掉原始中间材料

## OpenAI：Inside OpenAI's In-House Data Agent 核心三点

来源文章：<https://openai.com/index/inside-our-in-house-data-agent/>

### 核心一：Memory 只是整个 Context Stack 里的一个层

OpenAI 在这篇文章里没有把 memory 单独神化，而是把高质量 Agent 所依赖的上下文拆成六层：

- Table usage
- Human annotations
- Codex enrichment
- Institutional knowledge
- Memory
- Runtime context

这说明一个关键判断：

`memory` 不是全部上下文，也不是全部知识，只是整个上下文系统中的一层。

### 核心二：真正重要的 Memory 是“纠偏知识”

OpenAI 文中的 memory，主要不是聊天记录，也不是普通文档，而是那些很难从 schema、日志或文档中直接推断出来，但对结果正确性非常关键的经验性约束，例如：

- 某个实验过滤条件的真实定义
- 某类指标在特定场景下的口径规则
- 用户纠正过一次、下次还应复用的判断

也就是说，memory 最适合保存的是：

- 难推断
- 易反复犯错
- 对正确性影响很大

的那部分知识。

### 核心三：强 Agent 依赖分层上下文、在线求证和持续评测

OpenAI 这篇文章强调，单靠静态知识库不够。更强的 Agent 通常要同时具备：

- 离线整理好的多层知识
- 在线按需检索和查询真实系统的能力
- 在执行过程中自我检查和修正的能力
- 通过 evals 持续验证效果

也就是说，好的 memory 系统不是“存得多”，而是：

1. 能把不同类型的上下文分层管理
2. 能在需要时实时验证
3. 能把反复出现的关键经验沉淀成 memory

## Anthropic：Memory Tool 工程要点

来源文档：<https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool>

### 1. Memory 应该是外部持久层，不要依赖 transcript

Anthropic 这篇文档最重要的落点之一是：memory 不是模型“自动记住”历史，而是通过工具把信息写到一个外部持久层中，例如文件系统、数据库或云存储。

这样做的意义是：

- 不需要把完整对话历史一直塞进上下文
- 可以跨 session 恢复状态
- 可以把 memory 作为独立于 transcript 的长期状态层

### 2. 会话开始先读 memory，再开始行动

文档明确要求，启用 memory tool 后，Claude 在开始任务前应先查看 memory directory，理解已有记录，再决定接下来做什么。

这背后的工程原则是：

- 新会话不要从零猜测现场状态
- 先恢复上下文，再继续执行
- memory 应作为任务恢复入口，而不是事后补充材料

### 3. Memory 里应存“高价值状态”，不要堆原始输出

更适合写入 memory 的内容包括：

- 当前任务进度
- 已做出的关键决策
- 后续必须遵守的约束
- 用户偏好和反馈
- 未来会重复用到的知识

不适合直接塞进 memory 的内容包括：

- 大段原始日志
- 大量工具输出
- 一次性的中间结果
- 没有整理过的碎片化材料

也就是说，memory 更像“可恢复状态和可复用知识”，而不是“原始痕迹存档”。

### 4. Memory 不只是存储，还必须可维护

文档里定义的 memory 操作不只是读取和追加，还包括：

- 创建
- 修改
- 插入
- 重命名
- 删除

这说明 Anthropic 把 memory 视为可维护的工作空间。它不应该只增不减，而应该能够：

- 持续整理
- 淘汰过期内容
- 合并重复记录
- 保持结构清晰

### 5. 要和 Context Editing 配合使用

Anthropic 的完整思路不是只加一个 memory 层，而是让 `memory tool` 和 `context editing` 一起工作：

- `context editing` 负责清理旧的 tool outputs
- `memory tool` 负责保留那些不能丢的关键信息

推荐工作流是：

1. 发现上下文快满
2. 先提炼关键进度和结论
3. 写入 memory
4. 再清掉旧的原始上下文材料

这样系统才能做到“既能遗忘，又不丢关键状态”。

### 6. 把 Memory 当成多 Session Handoff 机制

这篇文档对软件开发场景特别实用的一点是，它鼓励把 memory 当作 session 之间的交接机制。

例如可以在 memory 中保留：

- 当前 feature 的进度记录
- checklist
- 已知问题
- 下一步计划
- 恢复工作的入口说明

这样下一个 session 启动时，可以先读 memory，再继续推进，而不是重新探索整个上下文。

### 7. Memory 强依赖工程安全边界

Anthropic 这篇文档还特别强调，memory 不是抽象概念，而是真实的文件或存储接口，因此必须自己处理好这些问题：

- 路径安全，避免访问 `/memories` 目录之外的内容
- 敏感信息控制，不要把隐私或密钥直接写入 memory
- 文件膨胀控制，避免 memory 目录无限增长
- 过期清理策略，防止长期累积无效内容

也就是说，memory 越强，越要把它当成正式存储系统来治理。

## OpenAI：Compaction 精简总结

来源文档：<https://developers.openai.com/api/docs/guides/compaction>

### 它解决什么问题

`Compaction` 解决的是会话太长、上下文不断膨胀的问题。它的作用不是长期记忆，而是把当前会话压缩成一个更小、还能继续推理的状态。

可以把它理解为：

- `conversation state` 负责延续会话
- `compaction` 负责在会话太长时压缩会话状态

### 它怎么用

OpenAI 提供两种方式：

- server-side compaction：到达阈值后由服务端自动压缩
- standalone compact endpoint：由开发者主动调用压缩接口

它更适合这些场景：

- 长轮数对话
- 长链路 agent
- 长时间 coding 或 research session

### 它不是什么

`Compaction` 不是：

- 长期 memory
- 外部知识库
- 可读的人工摘要

它更像一个平台内部维护的“短期状态压缩机制”。

### OpenAI 公开了什么，没有公开什么

官方公开说明了这些点：

- compaction 会减少上下文大小
- 会保留后续轮次需要的关键状态
- 会返回一个 `encrypted compaction item`
- 这个 item 是 `opaque` 的，应原样继续使用

但官方没有公开具体压缩算法，例如：

- 如何判断哪些内容是高价值内容
- 具体如何压缩 reasoning、messages、tool outputs
- 内部使用的是哪种摘要或状态表示方式

所以目前更准确的理解是：

- OpenAI 公开了 compaction 的接口和使用方式
- 但没有公开 compaction 的内部实现细节

## OpenAI：Conversation State 精简总结

来源文档：<https://developers.openai.com/api/docs/guides/conversation-state>

### 它解决什么问题

`Conversation state` 解决的是“如何延续会话”的问题。它的目标不是长期记忆，而是让模型在后续轮次中继续使用前面的对话和工具执行状态，而不需要开发者每次都手动重传完整历史。

可以把它理解为：

- `conversation state` 负责托管当前会话状态
- `compaction` 负责在状态过长时压缩它

### 它怎么用

OpenAI 文档里主要有两种方式：

- `previous_response_id`
  适合沿着上一轮继续对话，不必自己重新拼接历史
- `conversation`
  适合把一个长期存在的会话对象交给平台托管

如果不使用这两种方式，也可以自己手动传完整历史消息，但工程负担更大。

### 它适合什么场景

`Conversation state` 更适合这些场景：

- 普通多轮聊天
- 连续 agent 任务
- 需要托管会话上下文的应用
- 跨轮次延续 tool calls 和工具执行结果的场景

### 它不是什么

`Conversation state` 不是：

- 长期 memory
- 用户知识档案
- 外部知识检索系统

它更像一个“平台托管的短期会话状态层”。

### 使用上的几个关键点

- 用 `previous_response_id` 时，本质上是在“接着上一轮”继续
- 用 `conversation` 时，本质上是在“挂到一个长期会话对象”上继续
- 即使平台帮你托管 state，相关输入 token 依然会计费
- 如果会话继续膨胀，通常要结合 `compaction` 一起使用

### 一句话理解

OpenAI 的 `conversation state` 不是神秘 memory，而是让平台帮你托管和延续当前会话的上下文状态。

## 一句话总结

不要让模型记住一切，而要让系统决定什么该遗忘、什么该持久化、什么该实时求证。
