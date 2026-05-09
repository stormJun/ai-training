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

## Runnable 的常用接口

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
