# Prompt 模板概览

这一节不再把 Prompt 模板理解成“带几个 `{变量}` 的字符串”，而是把它看成 LLM 应用里的输入装配层。对于已经会写基础 Prompt 的工程实践者，重点不是语法能不能写出来，而是：

- 什么时候该用哪一种模板
- 怎么把固定指令、动态输入、对话历史、示例样本拆开组织
- 怎么避免 Prompt 越写越长、变量越来越乱、上下文越来越不可控

## Prompt 模板在工程里的定位

Prompt 模板本质上承担三件事：

1. 把稳定指令和运行时变量分离
2. 把多来源上下文按结构组装给模型
3. 让 Prompt 能被复用、测试、组合，而不是散落在代码里的大字符串

如果只是临时实验，直接写字符串问题不大；一旦进入可维护代码，Prompt 模板更像“请求构造器”。

## 选型总结

### 1. 只有一段文本时：优先 `PromptTemplate`

适合：

- 单轮任务
- 输入结构简单
- 最终发给模型的内容本来就是一整段文本

典型场景：

- 文本分类
- 信息抽取
- 摘要、改写、翻译

这类模板的核心是“生成一段最终字符串”，通常用 `PromptTemplate.from_template(...)` 即可。

### 2. 有 system / human / history 分层时：优先 `ChatPromptTemplate`

适合：

- 聊天模型
- 需要区分系统指令、用户问题、示例消息、历史消息
- 后续要接 Runnable / Chain / Agent

典型场景：

- 对话机器人
- RAG 问答
- Tool Calling 前的消息组织
- 带历史上下文的任务链

工程上，`ChatPromptTemplate` 通常应该是默认选项。因为很多后续能力都不是“单字符串”，而是“多消息结构”。

### 3. 有历史消息或中间消息块时：用 `MessagesPlaceholder`

适合：

- 对话历史注入
- Agent scratchpad 注入
- 工具调用前后的消息回填
- 把检索结果包装成一组消息而不是硬拼字符串

它的价值不是“占位”，而是让动态消息块成为模板的正式组成部分，而不是用字符串拼接偷偷塞进去。

### 4. 要管理示例样本时：用 few-shot 模板

适合：

- 结构化输出示例驱动
- 任务风格对齐
- 让模型学习输入输出格式

常见选择：

- `FewShotPromptTemplate`
- `FewShotChatMessagePromptTemplate`

当示例本身也是多轮消息时，优先用 chat 版本；当示例只是文本片段时，普通 few-shot 即可。

### 5. 只有在内置模板不够时，才继承 `StringPromptTemplate`

自定义模板类适合：

- 输入需要先做校验和归一化
- Prompt 生成本身包含条件逻辑
- 希望把模板配置做成一个可复用对象

这也是当前目录 `09`、`10`、`12` 这几份示例代码想表达的重点：不是所有 Prompt 都要继承，但当 Prompt 开始承载业务规则时，封装成类会更稳。

## LangChain 原生语法能力总结

下面不是逐个 API 教程，而是工程里最常用、最值得掌握的能力清单。

### 1. `PromptTemplate`：单文本模板

常见写法：

```python
from langchain_core.prompts import PromptTemplate

prompt = PromptTemplate.from_template(
    "请总结下面文本的主题，并给出三个关键词：\n\n{text}"
)
```

适合把“固定框架 + 运行时变量”分开管理。默认模板语法是 f-string 风格的 `{variable}`。

工程建议：

- 变量名要表达语义，例如 `question`、`context`、`schema`
- 不要把多个不同来源的信息都塞进一个 `input`
- 模板越短越好，复杂性应交给上游预处理

### 2. `ChatPromptTemplate`：多消息模板

常见写法：

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个严谨的代码评审助手。"),
    ("human", "请评审下面代码：\n{code}")
])
```

它的核心优势不是“也能写模板”，而是把消息角色结构保留下来。对聊天模型来说，这通常比把所有内容压成一个字符串更清晰。

工程建议：

- system 放稳定约束
- human 放本轮任务输入
- history 用 `MessagesPlaceholder`
- 检索上下文如果很长，优先作为独立变量插入到某条消息里，而不是混进所有消息

### 3. `MessagesPlaceholder`：注入消息列表

常见写法：

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个多轮问答助手。"),
    MessagesPlaceholder("history"),
    ("human", "{question}")
])
```

这比手动把历史拼接成一大段文本更规范，原因有两个：

- 消息角色不会丢
- 下游组件更容易约定输入格式

适用边界：

- `history` 是消息列表，不是普通字符串
- 如果只是少量静态示例，不需要为了“看起来高级”就强上 placeholder

### 4. partial variables：预绑定稳定变量

当某些变量是“模板级固定配置”，而不是“每次调用都要传入”的时候，可以做 partial 绑定。

适合：

- 固定输出语言
- 固定领域背景
- 固定格式要求
- 固定 schema 片段

工程价值：

- 减少调用点重复传参
- 避免上游遗漏关键变量
- 让模板对象本身具备环境语义

### 5. few-shot 模板：管理示例，而不是复制粘贴

Few-shot 的关键不是“多写几个例子”，而是让示例成为可维护结构。

适合：

- 需要稳定输出格式
- 需要模型学习分类边界
- 需要把高质量样本沉淀成资产

不适合：

- 示例和当前任务弱相关
- 示例过长，挤占真正任务上下文
- 用 few-shot 代替明确指令

### 6. 自定义 `StringPromptTemplate`：把 Prompt 封装成组件

这条路线适合把 Prompt 做成“带输入校验、条件逻辑、配置管理”的对象，而不是临时字符串。

当前目录里：

- `09_prompt_template_simple_demo.py`
  - 展示最小自定义模板
- `10_prompt_template_engineering.py`
  - 展示带 Pydantic 校验和条件逻辑的工程化版本
- `11_prompt_template_usage_demo.py`
  - 展示使用方式
- `12_prompt_template_advanced.py`
  - 展示更进一步的扩展能力

这种方式的价值不是“更面向对象”，而是当 Prompt 已经和业务字段、校验规则、配置文件耦合时，它比随处写 `format()` 更可维护。

## 工程实践里的组织原则

### 1. 把指令、数据、历史分层

推荐分法：

- 指令层：角色、目标、约束、输出要求
- 数据层：上下文、输入文本、结构化字段
- 历史层：对话消息、Agent 中间轨迹

最常见的问题，是把这三层全部揉成一个大字符串，最后没人知道哪个部分是稳定规则，哪个部分是运行时数据。

### 2. 变量名要稳定，不要让上游靠猜

差的变量名：

- `input`
- `data`
- `content`
- `text1`

更好的变量名：

- `question`
- `retrieved_context`
- `document_text`
- `output_schema`
- `conversation_history`

Prompt 模板本质上就是接口，变量命名越模糊，接口越脆弱。

### 3. 历史消息不要手工拼接

如果你已经在用聊天模型，却还在做这种事：

```python
history_text = "\n".join(messages)
prompt = f"历史记录如下：\n{history_text}\n\n用户问题：{question}"
```

那通常说明模板层次已经退化了。优先改成 `ChatPromptTemplate + MessagesPlaceholder`。

### 4. few-shot 是补充，不是主干

很多人把 few-shot 当成“提示词增强万能药”，结果模板越来越长、效果越来越不稳定。

更稳的做法：

- 先把任务目标写清楚
- 再决定是否需要示例
- 示例只保留最能体现边界和格式的少量样本

### 5. Prompt 模板应该和上游预处理配合

Prompt 不是万能清洗器。不要把以下问题都丢给模板层解决：

- 原始文本太脏
- 检索内容重复
- 结构化字段缺失
- 输入类型混乱

正确做法通常是：

- 上游先做清洗、裁剪、结构化
- 模板只负责表达任务和组装上下文

### 6. 模板要能被测试

最基础的测试不是跑模型，而是验证模板生成结果：

- 缺少变量时是否能及时报错
- 条件分支是否按预期拼装
- 输出 Prompt 是否包含关键约束
- 历史消息和示例消息是否插入到正确位置

这也是把 Prompt 从“字符串”升级为“组件”的重要标志。

## 常见反模式

### 1. 一个模板兼容所有任务

表面上减少了模板数量，实际上会让变量、条件分支、说明文字越来越乱。通常应该按任务边界拆分模板，而不是做一个“万能模板”。

### 2. system 里塞太多业务数据

system 更适合放长期稳定规则。大量动态上下文塞进 system，容易让角色约束和数据内容混在一起。

### 3. 把检索结果直接原样全贴进去

RAG 里最常见的问题不是“没上下文”，而是“上下文太多、太散、太脏”。模板层应该假设输入上下文已经经过筛选，而不是无脑扩大上下文。

### 4. 依赖模板技巧掩盖任务定义不清

如果任务目标本身含糊，再高级的模板结构也救不了结果质量。Prompt 工程很多时候不是“怎么写花”，而是“把任务定义写清楚”。

### 5. 过早自定义模板类

如果一个任务只是简单的单轮文本填空，直接用 `PromptTemplate` 或 `ChatPromptTemplate` 更合适。自定义类应该留给那些真的需要校验、配置、条件逻辑的场景。

## 一个实用的选型顺序

实际开发里，可以按下面顺序判断：

1. 能不能用 `PromptTemplate` 解决单文本任务
2. 只要涉及聊天模型和多消息结构，就优先升级到 `ChatPromptTemplate`
3. 只要有历史消息或中间消息块，就引入 `MessagesPlaceholder`
4. 需要示例驱动时，再补 few-shot
5. 只有当模板开始承载业务逻辑时，才考虑自定义 `StringPromptTemplate`

这套顺序的核心思想是：先用 LangChain 内置结构能力，再考虑自定义封装，不要一上来就把 Prompt 变成复杂类层级。

## 和当前目录示例的对应关系

- `08_prompt_template_text.txt`
  - 最基础的模板文本材料
- `09_prompt_template_simple_demo.py`
  - 自定义 `StringPromptTemplate` 的最小示例
- `10_prompt_template_engineering.py`
  - Prompt 组件化、参数化、校验化
- `11_prompt_template_usage_demo.py`
  - 模板实例化和调用方式
- `12_prompt_template_advanced.py`
  - 更复杂的工程能力扩展

建议学习顺序：

1. 先理解 `PromptTemplate` 和 `ChatPromptTemplate` 的选型逻辑
2. 再看 `MessagesPlaceholder` 和 few-shot 在复杂场景里的位置
3. 最后再看自定义 `StringPromptTemplate` 为什么适合工程封装

## 一句话总结

Prompt 模板不是为了“少写几个 f-string”，而是为了把模型输入组织成可维护、可组合、可验证的结构。对 LangChain 来说，真正重要的不是会不会写模板，而是能不能选对模板层级，并把指令、数据、历史、示例分开管理。
