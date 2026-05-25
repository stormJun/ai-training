# RAG 工作流基础

这一节不是只讲“检索 + 生成”两个动作，而是讲：

> 当你把 RAG 真正做成一个工作流时，中间还需要哪些判断与控制步骤。

原始材料里包含了大量 notebook 安装说明、运行输出和中间实验结果。这里整理后的重点是把主线保留下来，让你能顺着理解整个流程。

---

## 这一节讲什么

这个示例实现的是一个带控制逻辑的 RAG 工作流，主要包含这些环节：

1. 文档加载与向量化
2. 问题路由
3. 检索结果评分
4. 基于上下文生成答案
5. 幻觉检查
6. 答案有效性检查
7. 必要时回退到 Web 搜索

所以它不是一个“单次 prompt 调模型”的例子，而是一张真正的工作流图。

---

## 运行前提

这份材料依赖比较多，建议在本专题自己的环境里运行，而不是直接在全局 Python 环境里试。

通常至少需要：

- `DASHSCOPE_API_KEY`
- `langgraph`
- `langchain-community`
- `langchain-nomic`
- `scikit-learn`
- `bs4`
- `tavily-python`

如果要跑 Web 搜索分支，还需要：

- `TAVILY_API_KEY`

脚本里也保留了：

- Langfuse 可选追踪
- LangSmith 可选追踪

如果不配置，它们会自动降级关闭。

---

## 第一步：先把知识库建起来

这个示例先从几篇公开网页里构建本地知识库，内容包括：

- AI Agent
- Prompt Engineering
- LLM 对抗攻击

流程是：

1. 用 `WebBaseLoader` 把网页内容拉下来
2. 用 `RecursiveCharacterTextSplitter` 切分成文档块
3. 用 `NomicEmbeddings` 做向量化
4. 用 `SKLearnVectorStore` 构建本地向量存储
5. 再包装成检索器

这一步的作用是给后面的 `vectorstore` 路由准备离线知识源。

---

## 第二步：不是所有问题都该走向量检索

很多初学者做 RAG 时，默认所有问题都先检索文档再生成。

但这个示例专门加了一个 `Router`，让模型先判断：

- 这个问题适合走本地知识库
- 还是更适合走网络搜索

例如：

- “What are the types of agent memory?”
  更适合走本地向量库
- “What are the models released today for llama3.2?”
  更适合走实时 Web 搜索

这里想强调的是：

> RAG 的第一步不一定是检索，而可能是“先决定去哪里检索”。

---

## 第三步：检索出来的文档不一定都能用

即使问题被路由到向量库，检索出来的文档也可能不够相关。

所以示例里又加了一个 `Retrieval Grader`，用来判断每篇文档是不是和问题真正相关。

它的作用是：

- 过滤掉不相关文档
- 如果发现文档质量不够，就给后续流程打上一个“需要 Web 搜索补充”的标记

这一步非常重要，因为很多 RAG 失败并不是“模型不会答”，而是：

> 检索阶段给了错误上下文。

---

## 第四步：有了文档之后再做生成

当通过评分器筛出相关文档之后，流程才会进入生成阶段。

这里的生成逻辑很标准：

- 把文档拼成 `context`
- 把问题拼进 prompt
- 让模型只基于给定上下文回答

这一步是传统意义上的 RAG：

```text
documents + question -> prompt -> generation
```

但这还不是整个流程的结束。

---

## 第五步：生成之后还要检查“有没有胡说”

示例里专门加了 `Hallucination Grader`。

它会拿两样东西去做判断：

- 检索到的事实文档
- 模型生成的答案

然后判断：

- 回答是不是基于文档
- 有没有超出文档范围胡乱补充

也就是说，这一步解决的是：

> 模型虽然生成了答案，但这个答案到底是不是“站得住”。

---

## 第六步：即使不幻觉，也可能没答到点子上

有时候模型生成内容并不幻觉，但仍然没有真正回答问题。

所以示例里又加了 `Answer Grader`，继续检查：

- 回答有没有正面回应用户的问题

这个设计很工程化，因为它把两个问题拆开了：

- 是否基于事实
- 是否回答到位

这比只做一次粗糙判断更稳。

---

## 第七步：必要时回退到 Web 搜索

如果向量库检索结果不够好，或者生成出来的答案不够有用，工作流不会立刻结束，而是可能回退到：

- `websearch`

然后把 Web 搜索结果补进文档，再尝试重新生成。

所以这套流程不是直线，而是带回路的：

```text
route
  -> retrieve
  -> grade_documents
  -> generate
  -> grade_generation
  -> useful / retry / websearch / end
```

这就是 LangGraph 比普通链式调用更适合做 RAG 的原因之一：

> 它能把“检索、判断、回退、重试”统一放进一张图里。

---

## 最终图结构

从整体上看，这个工作流大致可以理解成：

```text
question
  -> route_question
  -> retrieve | websearch
  -> grade_documents
  -> generate
  -> hallucination / answer grading
  -> useful | retry | websearch | end
```

它已经具备一个真实 RAG 系统的典型要素：

- 多数据源
- 多级判断
- 可重试
- 可回退

---

## 脚本里保留了哪些关键模块

完整实现见同目录脚本：

- `09_RAG工作流_基础.py`

脚本里保留了这些核心部分：

- `router_instructions`
- `doc_grader_instructions`
- `rag_prompt`
- `hallucination_grader_instructions`
- `answer_grader_instructions`
- `GraphState`
- 检索 / 搜索 / 生成 / 评分节点
- 最终 `StateGraph` 编排

这意味着你既可以把它当文档读，也可以继续沿着脚本看完整实现。

---

## 怎么运行

直接运行脚本：

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/02_workflows/tutorials/04_rag_workflows
python 09_RAG工作流_基础.py
```

它会先：

- 初始化本地知识库
- 构建工作流图

然后跑两个示例：

1. 一个更偏知识型的问题
2. 一个更偏时效型的问题（如果配置了 `TAVILY_API_KEY`）

如果没配 `TAVILY_API_KEY`，当前事件相关的 Web 搜索部分会自动跳过。

---

## 这一节真正要学的点

- RAG 不只是“检索 + 生成”
- 真正工程化的 RAG 通常需要：
  - 路由
  - 检索结果评分
  - 幻觉检查
  - 答案质量检查
  - 回退和重试
- LangGraph 很适合承载这类有判断、有回路的流程

---

## 小结

这一节把 RAG 从“一个 prompt 技巧”提升成了“一个工作流系统”。

如果你读完之后能回答下面两个问题，就说明主线抓住了：

1. 为什么很多 RAG 系统需要先做路由？
2. 为什么生成答案之后还要继续评分和回退？

这两个问题，正是简单 RAG demo 和工程化 RAG 工作流之间的分界线。  
