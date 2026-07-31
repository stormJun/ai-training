# 自定义输出解释器

这一节展示如何在 LangChain 中定义自定义输出解析器。

## 主要思路

把模型输出先约束成一个固定结构，再由解析器把文本转换为 Python 对象。

这里的示例使用了“项目周报”场景：

- 项目名称
- 进度状态
- 已完成任务
- 待完成任务
- 风险点

## 用到的核心组件

- `StringPromptTemplate`
- `BaseOutputParser`
- `Pydantic` 数据模型

## `BaseOutputParser` 是怎么用的

`BaseOutputParser` 的核心作用，是把模型输出的原始文本，转换成你真正想在代码里使用的结构化结果。

最常见的使用方式只有三步：

1. 先定义目标结果类型  
   可以是：
   - `list[str]`
   - `dict`
   - `bool`
   - `Pydantic` 模型
   - 你自己的业务对象

2. 继承 `BaseOutputParser[T]`  
   其中 `T` 表示解析后返回的目标类型。

3. 实现 `parse(text: str)`  
   这个方法接收模型输出的文本，并返回结构化结果。

一个最小思路可以概括成：

```python
class MyParser(BaseOutputParser[TargetType]):
    def parse(self, text: str) -> TargetType:
        # 解析 text
        return parsed_result
```

这意味着 `BaseOutputParser` 并不负责“让模型按要求输出”，它只负责“拿到输出之后怎么解释”。

## 当前示例里怎么用

当前目录的 [15_custom_output_parser.py](../15_custom_output_parser.py) 用的是一个“项目周报”场景：

- `ProjectReport`
  - 定义结构化结果的数据模型
- `ProjectReportTemplate`
  - 负责生成固定格式的文本
- `ProjectReportParser`
  - 负责把文本解析回 `ProjectReport` 对象

其中真正体现 `BaseOutputParser` 用法的是这部分：

```python
class ProjectReportParser(BaseOutputParser[ProjectReport]):
    def parse(self, text: str) -> ProjectReport:
        ...
        return ProjectReport(...)
```

这里的意思是：

- 解析器最终返回的是 `ProjectReport`
- 输入是模型输出文本 `text`
- 解析逻辑由你自己定义

这个示例里，解析策略很简单：

1. 先按行拆分文本
2. 找出每一行里的 `字段名：字段值`
3. 再把 `已完成任务`、`待完成任务`、`风险点` 按 `、` 切成列表
4. 最后构造成 `ProjectReport`

## 为什么它要和 Prompt 配套设计

输出解析器能不能稳定工作，很大程度取决于 Prompt 是否把输出格式约束清楚。

这也是为什么这个示例不是“单独写一个 parser”，而是“模板 + 解析器”一起出现：

- Prompt 负责约束格式
- Parser 负责把格式化文本转回结构化对象

如果 Prompt 没把格式写清楚，parser 往往会变得脆弱：

- 字段名一变就解析失败
- 分隔符一变就切分错误
- 少一行内容就可能返回空值

所以在工程里，输出解析器通常不是单独设计的，而是和 Prompt 一起设计。

## 在代码里通常怎么调用

最直接的用法是手工调用 `parse()`：

```python
parser = ProjectReportParser()
result = parser.parse(raw_text)
```

这也是当前示例采用的方式。它先用模板构造出一段文本，再立刻交给 parser，帮助你先理解“输入格式”和“解析逻辑”的对应关系。

在真实链路里，通常会变成：

```python
prompt -> model -> parser
```

也就是说：

1. Prompt 生成提示词
2. 模型返回文本
3. Parser 把文本转成结构化对象

## 在实际项目里怎么对照理解

如果把这个思路放到真实项目里，可以把它和 DeerFlow 这类代码库对照着理解。

教程里的标准思路是：

```text
prompt -> model -> parser
```

也就是：

- Prompt 负责约束输出格式
- 模型负责生成文本
- Parser 负责把文本解释成结构化对象

但在很多实际项目里，未必真的会单独引入 `BaseOutputParser` 这一层。常见的另一种写法是：

```text
prompt -> model -> 手工解析逻辑
```

例如：

- 简单文本输出  
  Prompt 直接要求 `Return ONLY the title`，然后代码自己做去引号、去思维标签、截断等清洗。

- JSON 结构输出  
  Prompt 直接要求 `Return ONLY valid JSON`，然后代码自己 `json.loads(...)`，再把结果交给业务逻辑处理。

所以你可以这样理解这两种写法的关系：

- `BaseOutputParser` 方案  
  是把“解释模型输出”这件事，抽成一个独立组件

- 手工解析方案  
  是把“解释模型输出”这件事，直接写在当前业务函数里

本质上，两者解决的是同一个问题：

- 模型输出不能一直只停留在字符串层面
- 最终还是要进入代码里的结构化数据或业务对象

区别只在于：

- 你是用单独的 parser 封装这一步
- 还是把这一步直接写进业务代码

这也是为什么在工程里，`BaseOutputParser` 不是“必须使用”的组件，而是一种更清晰的组织方式。

## 什么时候适合自定义 `BaseOutputParser`

适合：

- 模型输出是半结构化文本
- 你已经能比较稳定地约束输出格式
- 你想把解析逻辑封装成独立组件
- 你希望最后拿到的是业务对象，而不是原始字符串

常见场景：

- 周报 / 日报 / 分析报告
- 工单分类
- 文本规则抽取
- 自定义表格、列表、标签结果

## 它的局限在哪里

这个方式很直观，但也有明显局限：

- 解析强依赖输出格式稳定
- 模型只要轻微偏离格式，解析就可能失败
- 规则越复杂，手写 parser 越难维护

所以 LangChain 现在的官方建议是：

- 如果模型支持原生 structured output，就优先使用模型原生能力
- 自定义 `BaseOutputParser` 更适合那些不能直接走原生结构化输出、或者你需要额外后处理的场景

也就是说，`BaseOutputParser` 现在更像：

- 一种可控的文本后处理机制
- 一种自定义结构化适配层

而不是所有结构化输出场景下的默认首选。

## 这个示例最想表达什么

这一节最核心的目标，不是教你写一个复杂 parser，而是让你理解下面这件事：

模型输出如果要进入工程代码，最好不要一直停留在“字符串”层面。

更理想的流程是：

1. 先用 Prompt 约束输出格式
2. 再用 Parser 把输出解释成结构化数据
3. 最后在业务代码里操作对象，而不是继续操作原始文本

## 价值

自定义输出解析器适合：

- 报告生成
- 结构化摘要
- 工单分类
- 规范格式输出
