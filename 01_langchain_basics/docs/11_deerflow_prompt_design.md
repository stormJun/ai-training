# DeerFlow Prompt Template 设计落地

这篇文档不是再讲一遍“Prompt 模板是什么”，而是把 DeerFlow 里已经落地的一套 prompt template 设计方法，整理成适合在训练营仓库里学习和复用的工程案例。

如果说 [06_prompt_template_overview.md](/Users/songxijun/workspace/otherProject/ai-training/01_langchain_basics/06_prompt_template_overview.md) 重点在 LangChain 里的模板选型，那么这篇更关注另一个问题：

- 当项目已经从“几个 Prompt 示例”发展成一个完整 agent 系统时，Prompt 应该如何分层？
- 哪些内容应该放进静态 system prompt？
- 哪些内容应该在运行时动态注入？
- 为什么有些项目不直接把一切都写成 LangChain `PromptTemplate` 对象树？

## 这篇文档讨论什么

这里讨论的是 DeerFlow lead agent 的 prompt template 设计，以及和它直接耦合的运行时组件。原始设计文档对应的核心代码主要包括：

- `backend/packages/harness/deerflow/agents/lead_agent/prompt.py`
- `backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- `backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py`
- `backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py`
- `backend/packages/harness/deerflow/agents/middlewares/title_middleware.py`
- `backend/packages/harness/deerflow/config/title_config.py`

这里不展开 DeerFlow 的所有 agent 细节，而是只提炼对 Prompt 工程最有价值的设计边界。

## 一句话总结

DeerFlow 的 prompt template 不是“一个越来越长的 system prompt 字符串”，也不是“把所有东西都抽成 LangChain `PromptTemplate` 对象”。

它采用的是一套分层设计：

1. 静态 system prompt 负责稳定规则
2. 可选 section 负责按能力和配置拼装说明块
3. 动态上下文通过 middleware 在运行时注入
4. title、summarization、memory 这些衍生能力再围绕 message history 做兼容处理

这套设计最重要的价值有两个：

- 保持主 system prompt 尽量稳定，利于 prefix cache 复用
- 把“会变的上下文”和“不会变的规则”硬性分开

## 把它映射到 LangChain 语境里看

如果只看 `01_langchain_basics` 这部分内容，我们通常会先学到：

- `PromptTemplate`
- `ChatPromptTemplate`
- `MessagesPlaceholder`
- few-shot 模板
- 自定义 `StringPromptTemplate`

这些能力更适合解决“如何组织一个 prompt”。

而 DeerFlow 这个案例解决的是更高一层的问题：当一个 agent 系统已经有了长对话、memory、title、skills、tool search、subagent 这些能力之后，Prompt 不再只是模板语法问题，而是系统架构问题。

所以 DeerFlow 的关键不在于“有没有用 LangChain PromptTemplate API”，而在于它把模型上下文拆成了几种来源：

- 稳定规则
- 配置型能力说明
- 当前用户和当前线程相关的动态上下文
- 由长对话、标题生成等逻辑派生出来的处理链

## DeerFlow 的四层分层

从职责上看，可以把这套实现拆成四层。

| 层 | 主要位置 | 主要职责 |
| --- | --- | --- |
| 静态模板层 | `lead_agent/prompt.py` | 定义稳定的主 system prompt 骨架，例如角色、工作方式、澄清规则、工作目录说明 |
| 装配层 | `lead_agent/prompt.py` + `lead_agent/agent.py` | 根据配置决定启用哪些 section、哪些 tools、哪些 middleware |
| 动态上下文层 | `dynamic_context_middleware.py` | 在真正调用模型前，把 memory、current date 等动态内容注入消息历史 |
| 兼容与衍生层 | `summarization_middleware.py`、`title_middleware.py` | 处理长对话压缩、标题生成，并保证它们不会误读隐藏上下文消息 |

可以把它简化理解成：

```text
静态规则 -> system prompt
能力开关 -> section 拼装
动态上下文 -> middleware 注入消息
后处理能力 -> 围绕 message history 做兼容
```

这比“所有内容都拼成一段 prompt 再发给模型”更稳，也比“所有内容都硬抽象成 PromptTemplate 树”更贴合当前项目复杂度。

## 运行链路怎么理解

DeerFlow 在一次请求中，大致按下面顺序工作：

1. lead agent 创建时先生成静态 system prompt
2. `apply_prompt_template()` 按配置拼好可选 section
3. agent 运行前，`DynamicContextMiddleware` 注入隐藏的动态上下文消息
4. 如果对话很长，summarization middleware 会压缩历史，但要保留这些隐藏上下文
5. 如果要生成标题，title middleware 会跳过隐藏上下文，只抽真正的用户消息和 AI 回复

简化后的心智模型可以记成：

```text
system prompt = 稳定规则 + 能力说明
message history = 动态上下文 + 用户消息 + AI/Tool 历史
```

这正是 DeerFlow 设计里最值得学习的地方。

## 一个具体例子

假设当前会话里存在这些条件：

- 当前日期是 `2026-05-12`
- memory 中已经知道用户偏好“简洁、技术化的解释”
- 当前用户问题是“帮我解释一下 DeerFlow 的 prompt template 是怎么设计的”

DeerFlow 不会把这些信息都塞进主 system prompt，而是更接近下面这种组织方式：

```text
System Prompt
  = 稳定规则
  + skills / subagent / tools / workspace 等能力说明

Hidden HumanMessage
  <system-reminder>
  <memory>
  User prefers concise technical explanations.
  </memory>
  <current_date>2026-05-12, Tuesday</current_date>
  </system-reminder>

Visible HumanMessage
  帮我解释一下 DeerFlow 的 prompt template 是怎么设计的
```

这个组织方式的好处是：

- 用户和日期变化时，不需要重写整个主 prompt
- 主 system prompt 仍然能在不同用户、不同线程之间复用
- memory、title、summarization 这些逻辑都能围绕 message history 工作

## 为什么这比“全部塞进 system prompt”更好

如果把 current date、memory、thread-specific context 都直接塞进 system prompt，会带来几个明显问题：

1. 主 prompt 每轮变化，缓存命中率下降
2. 同一个 agent 在不同用户或不同线程间的 prompt 无法复用
3. title、summarization、memory 等中间层很难区分哪些是稳定规则，哪些是会话态数据

所以 DeerFlow 把这条边界定得很清楚：

- 稳定规则进静态模板
- 动态上下文走 middleware 注入

这条边界比“模板语法写得漂亮”重要得多。

## 为什么 DeerFlow 没有把主 prompt 建成 LangChain `PromptTemplate` 对象树

这不是遗漏，而是一个有意的设计选择。

原因主要有四个：

1. 主体是一个大 system instruction 文档，按 section 拼接比 message graph 更直接
2. 当前最大的复杂度不在变量替换，而在“内容应该落在哪一层”
3. 项目需要和 skills、subagents、sandbox、tool search、自定义 agent 能力做大粒度组合，字符串 section 拼装已经足够
4. 直接使用普通 `.format(...)` 更方便仓库维护者改 prompt 文案

这也意味着 DeerFlow 的 prompt 设计重点不是“LangChain API 技巧”，而是“上下文治理”。

## 主模板与可选 section 的分工

从 DeerFlow 的实现方式看，可以把 prompt 内容再拆成两类。

### 1. 主骨架：稳定规则

主骨架里通常放这些东西：

- 角色定义
- 思考与响应风格
- 澄清规则
- 工作目录和环境说明
- 引用与输出要求
- 关键提醒

这类内容的共同点是：

- 对多数用户和线程都相同
- 修改频率低
- 适合长期缓存

### 2. 可选 section：按能力和配置拼装

DeerFlow 里常见的可选 section 包括：

- skills 说明
- deferred tools 说明
- subagent 规则
- ACP agent 工作区说明
- custom mounts 说明
- custom agent 的 `soul` / `self_update`

这些 section 的共同点是：

- 它们是“能力说明”
- 它们会随配置变化
- 但不会在同一线程的每一轮里频繁变化

所以它们应该进入 prompt 装配层，而不是进入动态上下文层。

## middleware 注入层为什么重要

在 DeerFlow 里，真正会随用户、线程、时间变化的内容，不直接改 system prompt，而是由 `DynamicContextMiddleware` 注入隐藏消息。

这个设计看起来只是“换个地方拼接”，但本质上是在保护系统边界。

它至少解决了三个问题：

1. 不污染主 system prompt 的稳定性
2. 让动态上下文以 message 的形式进入模型，和普通对话历史处于同一处理链
3. 让 title、summarization、memory 这些中间件可以显式识别和保留这些内容

这也是为什么在复杂 agent 项目里，Prompt 工程不能只盯着 `prompt.py`，还要看 message 级中间件。

## Summarization 和 Title 为什么必须跟进

这是 DeerFlow 设计里很容易被忽视，但非常实用的一点。

动态上下文提醒本质上也是消息。如果项目里还有：

- 长对话压缩
- 自动标题生成
- memory 提取或回填

那么这些逻辑都会直接读取 `messages`。

于是问题就来了：

- 如果 summarization 把动态提醒压缩掉，后续轮次可能会错误地重新注入
- 如果 title middleware 不跳过动态提醒，标题就可能不是从真正的首轮用户输入生成

所以 DeerFlow 的设计不是“只有一个 prompt”，而是“prompt 设计要和 message history 的后续处理链一起演化”。

## 关键设计决策，值得直接借鉴

### 1. 静态主 prompt 与动态提醒分离

这是最核心的一条。以后遇到类似需求，也建议先问：

- 这条信息是长期稳定规则，还是按会话变化的上下文？

如果是后者，优先考虑 middleware 注入，而不是继续扩主模板。

### 2. 使用 XML-like 标签，而不是纯自然语言散文

DeerFlow 的 `<role>`、`<memory>`、`<system-reminder>`、`<current_date>` 这类标签，不只是为了可读性，还为了：

- 方便后续字符串提取和匹配
- 帮助日志和调试工具识别边界
- 避免多个 section 混在一起

这对复杂 Prompt 系统非常有用。可读结构本身就是一种工程约束。

### 3. 技能类 prompt 做缓存，而不是在热路径上反复读盘

skills section 不只是“文案块”，它还涉及生成方式和刷新策略。DeerFlow 把技能 prompt 做缓存，核心考虑是：

- 请求路径要低延迟
- 磁盘扫描或配置读取不适合放在每次创建 agent 的热路径

这提醒我们：Prompt 组装不只是文本问题，也要考虑性能和缓存策略。

### 4. title prompt 单独演化，不复用主 lead prompt

标题生成是一个小而明确的任务，不需要把 lead agent 的全部 system prompt 搬过去。

这说明 prompt 体系里完全可以存在多个层级：

- 主任务 prompt
- 标题生成 prompt
- 压缩总结 prompt

不要为了“统一”而过度复用。

## 以后改 Prompt，应该怎么判断落点

DeerFlow 的经验可以总结成一套很实用的判断顺序。

### 1. 如果你要改的是稳定行为规则

例如：

- 修改澄清规则
- 修改 response style
- 修改引用规范
- 修改工作目录说明

优先改：

- 主 system prompt 骨架
- 或对应的静态 section builder

### 2. 如果你要加的是会话态动态上下文

例如：

- 当前日期
- 用户 profile
- session mode
- workspace snapshot

优先改：

- middleware 注入层
- 而不是 `apply_prompt_template()`

### 3. 如果你要加的是某种能力开关下的说明块

例如：

- 新的 tool family 说明
- 新的 agent mode 规则
- 新的实验能力说明

优先改：

- section builder
- 由 `apply_prompt_template()` 按配置装配

### 4. 如果你动到了隐藏 reminder 的格式

这是高风险改动。因为它通常会连带影响：

- 日期提取逻辑
- dynamic reminder 判定逻辑
- summarization 里的保留逻辑
- title middleware 对“真正用户消息”的识别逻辑

这种改动绝对不能只改一处 prompt 文案。

## 常见坑

### 1. 把动态数据重新塞回主 system prompt

短期省事，长期会让缓存、测试和多用户复用都变差。

### 2. 改 reminder 文案时顺手删了结构化标签

标签一删，后面的提取、识别、跨天更新逻辑都容易断。

### 3. 只改 Prompt，不看 summarization

很多问题在短对话里看不出来，只有长对话压缩时才暴露。

### 4. 以为前端隐藏了消息，下游逻辑就看不到

前端看不见不代表 title middleware、summarization middleware、memory 逻辑看不见。它们直接读的是 message history。

### 5. 新增模板占位符，但忘了在所有调用点传值

只要主模板还是基于 `.format(...)`，这个风险就一直存在。

### 6. 改技能 prompt 时忽略缓存刷新

这样会出现“有时生效、有时不生效”的偶发问题，最难排查。

## 对训练营仓库最有启发的几点

把 DeerFlow 放到 `01_langchain_basics` 里学习，最重要的不是记住它的全部实现细节，而是吸收下面几条方法论：

1. Prompt 工程的难点，后期往往不在模板语法，而在上下文分层
2. LangChain `PromptTemplate` 很适合单任务模板组织，但复杂系统还需要 middleware 级设计
3. system prompt 不应该无限膨胀，动态信息要找到独立注入层
4. 任何 message 级改动，都要同步审查 summarization、title、memory 这些后续能力
5. Prompt 设计要同时考虑缓存、可维护性、调试性和配置组合能力

## 推荐阅读顺序

建议把这一组材料连起来看：

1. [06_prompt_templates.md](/Users/songxijun/workspace/otherProject/ai-training/01_langchain_basics/06_prompt_templates.md)
2. [06_prompt_template_overview.md](/Users/songxijun/workspace/otherProject/ai-training/01_langchain_basics/06_prompt_template_overview.md)
3. `07_prompt_template_simple.py`
4. `08_prompt_template_engineering.py`
5. 这篇 `11_deerflow_prompt_design.md`

这样会形成一个更完整的层次：

- 先理解 LangChain 模板选型
- 再理解自定义模板工程化
- 最后理解复杂 agent 项目里的 prompt 分层设计

## 一句话收尾

DeerFlow 这个案例最值得学的，不是“Prompt 写得多复杂”，而是它始终守住了一条边界：

- 稳定规则进静态模板
- 动态上下文走 middleware 注入
- 配置型能力通过独立 section 拼装
- message 级改动同步考虑 summarization 和 title

一旦进入复杂 agent 系统，这条边界比任何单个 Prompt 技巧都更重要。
