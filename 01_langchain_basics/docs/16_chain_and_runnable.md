# 链与 Runnable 解析

这一节是本目录里最系统的一份 LangChain 语法说明，核心围绕“链”和“Runnable”展开。

## 什么是链

链可以理解为一条流水线，多个步骤依次连接：

1. 准备提示词
2. 调用模型
3. 解析输出
4. 返回结果

在 LangChain 中，最常见的写法就是：

```python
chain = prompt | model | parser
```

## 为什么 `|` 可以工作

LangChain 的 Runnable 对象实现了 `__or__` / `__ror__`，所以可以用管道语法连接组件。

### Python 里 `|` 的本质

在 Python 里，`|` 原本是“按位或”运算符，但它也支持运算符重载。

表达式：

```python
a | b
```

本质上会按下面顺序尝试：

1. 先调用 `a.__or__(b)`
2. 如果左侧对象不支持，或者没有适配右侧对象，再尝试 `b.__ror__(a)`

可以先记住一句话：

- `__or__` 处理“左对象 | 右对象”
- `__ror__` 处理“其他对象 | 当前对象”

### 原生行为：整数里的按位或

对整数来说，`|` 的原生含义是二进制按位或：

```python
print(5 | 3)  # 7
```

它等价于：

```python
5.__or__(3)
```

这也是 `|` 在没有被重载前最基础的行为。

### 自定义类里怎么重载 `__or__`

如果你定义了自己的类，就可以改写 `|` 的语义。

例如：

```python
class MyNum:
    def __init__(self, val):
        self.val = val

    def __or__(self, other):
        return MyNum(self.val + other.val)

a = MyNum(10)
b = MyNum(20)

res = a | b
print(res.val)  # 30
```

这里的 `a | b` 已经不再表示“按位或”，而是被改成了“两个对象相加后返回一个新对象”。

### `__ror__` 什么时候触发

`__ror__` 的作用，是给“右侧对象”补一个反向处理入口。

例如：

```python
class MyNum:
    def __init__(self, val):
        self.val = val

    def __or__(self, other):
        return MyNum(self.val + other.val)

    def __ror__(self, left_val):
        return MyNum(left_val * self.val)

res = 5 | MyNum(10)
print(res.val)  # 50
```

这里左边是 `int`，右边是 `MyNum`。由于左边的原生逻辑并不会按我们想要的方式处理 `MyNum`，于是 Python 会回头尝试右边对象的：

```python
MyNum(10).__ror__(5)
```

所以：

- `__or__` 是“我在左边时怎么处理”
- `__ror__` 是“我在右边时怎么处理”

### 回到 LangChain：为什么 `prompt | model | parser` 能成立

LangChain 正是利用了这个机制，把 `|` 从“按位或”重载成“Runnable 串联”。

也就是说：

```python
chain = prompt | model | parser
```

不是在做数学运算，而是在做链式组合：

1. `prompt` 先生成输入
2. `model` 接收 prompt，返回模型输出
3. `parser` 再把模型输出解释成目标结果

从语义上更接近：

```python
chain = prompt.__or__(model).__or__(parser)
```

如果某些对象在左边不是 Runnable，而右边是支持 LCEL 组合的对象，那么 `__ror__` 也可以参与进来，这就是为什么一些“非 Runnable 输入”也能被包装进 LangChain 组合体系。

### 这一段最重要的结论

理解 `__or__` / `__ror__` 的意义，不是为了背魔法方法名字，而是为了建立一个更清晰的认知：

- LCEL 的 `|` 本质上是 Python 运算符重载
- LangChain 只是把 `|` 改造成了“流水线拼接”语法
- 所以 `prompt | model | parser` 读起来像管道，底层其实还是对象方法调用

一旦明白这一点，后面再看 `RunnableParallel`、`RunnableBranch`、`RunnableLambda`，就会更容易理解：它们本质上都是在 Runnable 统一抽象之上的“组合与编排”能力。

## Runnable 是什么

`Runnable` 是 LangChain 里最核心的统一执行抽象。可以把它理解成：

“任何一个能够接收输入、执行处理、返回输出的组件，都可以被放进 Runnable 体系里。”

从这个角度看，很多看起来完全不同的对象，其实都可以归到同一类：

- `PromptTemplate`
- Chat Model / LLM
- Output Parser
- `RunnableLambda`
- `RunnableParallel`
- `RunnableBranch`

这也是 LangChain 设计里最关键的一点：它不是把 Prompt、模型、解析器分别看成三套互不相关的东西，而是把它们都统一成“可执行组件”。

### 为什么这个抽象重要

`Runnable` 最重要的价值有三个：

1. 统一调用方式  
   不同组件都尽量遵循同一套执行接口，例如：
   - `invoke`
   - `ainvoke`
   - `batch`
   - `stream`

2. 统一组合方式  
   因为它们都属于 Runnable，所以才能：
   - 串行组合：`prompt | model | parser`
   - 并行组合：`RunnableParallel(...)`
   - 条件分支：`RunnableBranch(...)`

3. 统一输入输出边界  
   Runnable 强调“输入是什么、输出是什么”，这样不同组件之间才能稳定拼接，而不是靠隐式约定凑在一起。

### 可以把它理解成流水线节点

一个非常实用的理解方式是：

- `PromptTemplate`：把结构化输入变成 prompt
- `Model`：把 prompt 变成模型输出
- `Parser`：把模型输出变成结构化结果

也就是说，它们虽然功能不同，但都满足同一种模式：

```text
输入 -> 处理 -> 输出
```

而这正是 Runnable 的核心。

### 一句话总结

Runnable 不是某一个具体组件，而是 LangChain 用来统一“执行”和“组合”的基础接口。

正因为 Prompt、Model、Parser 都能被看成 Runnable，LCEL 才能用统一的方式把它们串起来。

## RunnableSequence 是什么

`RunnableSequence` 就是 LangChain 里“串行执行的一条 Runnable 链”。

它的含义很直接：

- 前一个步骤的输出
- 自动变成下一个步骤的输入
- 多个 Runnable 按顺序一路传下去

最典型的例子就是：

```python
chain = prompt | model | parser
```

这条表达式背后，本质上构造出来的就是一个 `RunnableSequence`。

可以把它理解成：

```text
输入
 -> prompt
 -> model
 -> parser
 -> 最终结果
```

所以 `RunnableSequence` 的核心价值不是“多了一个新组件”，而是把多个原本独立的 Runnable 串成一条流水线。

### 它和 `Chain` 的关系

在学习时，可以先把两者近似理解成同一层意思：

- `Chain`：偏概念说法，表示“一条处理链”
- `RunnableSequence`：偏源码和框架实现里的正式类型名，表示“由多个 Runnable 串行组成的链”

也就是说，在 LangChain 0.3+ 的 Runnable 体系下，很多我们口头上说的“chain”，落到实现上往往就是 `RunnableSequence`。

### 它和 `RunnableParallel` 的区别

- `RunnableSequence`
  - 串行执行
  - 上一步输出喂给下一步输入
- `RunnableParallel`
  - 并行执行
  - 同一个输入同时发给多个分支

可以简单记成：

```text
RunnableSequence = 一条流水线
RunnableParallel = 一组并行分支
```

## Runnable 的常用接口

### Runnable 关系极简图

如果把 `PromptTemplate`、`Model`、`Parser`、`Chain`、`RunnableParallel` 放在一张图里，可以先这样理解：

```text
                Runnable
                   |
    -----------------------------------------
    |                  |                    |
PromptTemplate       Model                Parser
    |                  |                    |
    ----------- 串行组合：prompt | model | parser ----------
                               |
                             Chain
                               |
                        最终可 invoke / stream
                               |
              -------------------------------------
              |                                   |
      RunnableBranch                      RunnableParallel
      条件路由分支                         多路并行执行
```

如果换成“数据流”视角，可以再看成：

```text
输入参数
   |
   v
PromptTemplate
   |   把结构化输入变成 prompt
   v
Model
   |   把 prompt 变成模型输出
   v
Parser
   |   把模型输出变成结构化结果
   v
最终结果
```

而 `RunnableParallel` 的心智模型更像：

```text
            同一个输入
                |
                v
        -------------------
        |        |        |
        v        v        v
     分支A     分支B     分支C
        |        |        |
        --------合并结果--------
```

可以把这部分先记成一句话：

- `PromptTemplate`、`Model`、`Parser` 都是 `Runnable`
- `Chain` 是多个 `Runnable` 串起来
- `RunnableParallel` 是多个 `Runnable` 并起来
- `RunnableBranch` 是多个 `Runnable` 按条件选一路

- `invoke`
- `ainvoke`
- `batch`
- `stream`
- `RunnableParallel`
- `RunnableBranch`
- `RunnableLambda`

## 这一节覆盖的重点

- LCEL 管道语法
- schema 的意义
- `ainvoke` 的线程池原理
- `stream` 的逐步输出
- `batch` 的批处理
- 并行组合
- 条件分支
- 错误处理与容错
- 自定义 Runnable

## 学习建议

如果你是第一次看 LangChain 0.3+ 的写法，最值得优先掌握的是：

1. `prompt | model | parser`
2. `invoke / ainvoke / batch / stream`
3. `RunnableLambda`
4. `RunnableParallel`
5. `RunnableBranch`

如果你已经理解了 Runnable 的基本执行模型，下一步建议继续看：

- [17_runnable_config.md](./17_runnable_config.md)
  - 专门讲 `RunnableConfig` 的使用方式、常见字段，以及它在 LangChain 源码中的传播设计
- [18_deerflow_runnable_design.md](./18_deerflow_runnable_design.md)
  - 结合 DeerFlow 真实工程，解释 Runnable 在 agent runtime、middleware、tool 和 graph 执行链中的落点
