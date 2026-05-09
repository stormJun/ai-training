# 第一个对话链

这一节介绍 LangChain 中最基础的一条链通常由哪些部分组成。

## 核心组成

一条常见的处理链通常包含三个要素：

1. 语言模型：核心推理引擎
2. 提示词模板：负责组织输入
3. 输出解析器：把模型结果变成更容易处理的结构

## 语言模型

LangChain 中常见的模型分成两类：

- `LLM`：输入输出通常都是字符串
- `ChatModel`：输入输出通常是消息对象

常见消息类型包括：

- `HumanMessage`
- `AIMessage`
- `SystemMessage`
- `ToolMessage`
- `FunctionMessage`

## 提示词模板

提示词模板的作用是把变量填充进固定格式里，让同一套提示可以复用。

常见写法：

- `PromptTemplate.from_template(...)`
- `ChatPromptTemplate.from_messages(...)`

## 输出解析器

输出解析器负责把自然语言结果转成结构化数据，常见场景包括：

- 列表解析
- Pydantic 结构解析
- JSON 解析

## LCEL 的价值

LangChain Expression Language（LCEL）允许你用 `|` 把组件直接串起来，例如：

```python
chain = prompt | llm | parser
```

这样做的好处包括：

- 写法简洁
- 组件组合直观
- 易于扩展到并行、流式、批处理等高级能力
