# LangGraph 源码视角：State 底层如何传递数据

这篇文档只回答一个问题：

> **在 LangGraph 里，`state` 底层到底是怎么在节点之间传递的？**

很多初学者看到 `StateGraph` 会以为：

- 节点 A 接收一个 `dict`
- 改一下这个 `dict`
- 再把它直接传给节点 B

但 LangGraph 的真实实现不是这样。

LangGraph 底层是一个基于 `Pregel` 的运行时模型。`state` 在编译之后，会被拆成多个 `channel`，节点不是直接互相传递 Python 对象，而是通过：

```text
State Schema
  -> Channels
  -> Node Read
  -> Partial Update
  -> Channel Write
  -> Pregel Merge
  -> Next Step Read
```

也就是说：

> **节点之间传递的不是“完整 state 对象”，而是“对 state 中各个 key 的更新”，这些更新会由 Pregel 在 super-step 边界统一合并。**

---

## 1. 先看结论：LangGraph 的 state 不是直接传 dict

`StateGraph` 官方抽象层的签名是：

```python
State -> Partial[State]
```

也就是：

- 节点读取当前 state
- 节点返回的是一个**状态增量更新**
- 运行时负责把这些更新合并回共享状态

在源码中，这个设计直接写在 `StateGraph` 类注释里：

- `libs/langgraph/langgraph/graph/state.py`
- `The signature of each node is State -> Partial<State>`

这意味着节点函数虽然“看起来像在处理一个 state dict”，但底层并不是就地修改一个对象，而是：

1. 从 channel 系统中读出当前 state 快照
2. 节点返回更新值
3. 运行时把这些更新按 key 写回对应 channel
4. 下一轮节点再从这些 channel 读取新的 state

---

## 2. State Schema 会先被拆成 Channels

源码入口在：

- `libs/langgraph/langgraph/graph/state.py`
- `_get_channels(...)`
- `_get_channel(...)`

这一层做的事情是：把你定义的 state schema 中的每个字段，转换成一个底层 channel。

### 2.1 默认情况：字段会变成 `LastValue`

如果一个字段只是普通类型，例如：

```python
class State(TypedDict):
    query: str
    response: str
```

那么底层会默认使用 `LastValue` channel。

也就是说：

- `query -> LastValue(str)`
- `response -> LastValue(str)`

`LastValue` 的含义是：

- 当前 step 里只能接收一个更新值
- 最终保留“最后一个值”

这也是为什么如果同一个 step 里多个节点同时写同一个普通字段，会报并发更新错误。

相关源码：

- `libs/langgraph/langgraph/channels/last_value.py`

`LastValue.update(...)` 明确写了：

- 如果没有值，忽略
- 如果同一轮有多个值，抛 `InvalidUpdateError`
- 否则保留最后一个值

### 2.2 带 reducer 的字段：会变成 `BinaryOperatorAggregate`

如果你写的是：

```python
class State(TypedDict):
    steps: Annotated[list[str], operator.add]
```

那么 LangGraph 不会把它当作普通 `LastValue`，而是识别为一个带 reducer 的聚合字段。

底层会转成：

- `steps -> BinaryOperatorAggregate(list[str], operator.add)`

这类 channel 的特点是：

- 一轮里允许接收多个更新
- 会按 reducer 进行合并

例如多个节点都返回：

```python
{"steps": ["a"]}
{"steps": ["b"]}
```

最后会合成：

```python
["a", "b"]
```

相关源码：

- `libs/langgraph/langgraph/graph/state.py`
- `_is_field_binop(...)`
- `libs/langgraph/langgraph/channels/binop.py`

### 2.3 一句话理解这一层

可以把这一层理解成：

> **LangGraph 会把“逻辑上的 state 字段”编译成“物理上的 channel 存储单元”。**

所以 `state["messages"]`、`state["past_steps"]`、`state["response"]` 在底层都不是一个大 dict 的某个键值，而是不同的 channel。

---

## 3. `compile()` 之后，StateGraph 会变成一个 Pregel 系统

源码入口：

- `libs/langgraph/langgraph/graph/state.py`
- `StateGraph.compile(...)`

在 `compile()` 里，LangGraph 会构造一个 `CompiledStateGraph`，其父类就是 `Pregel`。

这里有两个关键动作：

### 3.1 把 channels 装入运行时

编译时会把这些内容放入运行时的 channel 集合中：

- 所有 state channels
- managed values
- 一个额外的 `START` channel

`START` 被包装成 `EphemeralValue(input_schema)`，专门用来承接 graph 的初始输入。

所以 graph 启动时，初始输入并不是“直接传给第一个节点”，而是：

```text
invoke(input)
  -> 写入 START channel
  -> 第一个节点从 START / 对应输入 channels 读取
```

### 3.2 给每个节点挂上 reader / writer

编译时对每个节点调用 `attach_node(...)`：

- 配置它要读哪些 channels
- 配置它要把输出写到哪些 channels
- 配置节点触发条件

这一层把一个 Python 节点函数变成了 `PregelNode`。

一句话理解：

> **编译完成后，每个节点不再只是一个普通函数，而是一个“从 channels 读、向 channels 写”的 Pregel actor。**

---

## 4. 节点是怎么读取 state 的

源码入口：

- `libs/langgraph/langgraph/pregel/_read.py`
- `ChannelRead`
- `PregelNode`

### 4.1 节点不会直接拿到底层原始存储

节点读取 state 时，运行时会先根据节点绑定的 `input_schema` 决定：

- 这个节点需要哪些 state keys
- 这些 key 对应哪些 channels

然后通过 `ChannelRead.do_read(...)` 从这些 channels 中读取值。

### 4.2 读取后还会做一次 mapper 转换

在 `attach_node(...)` 里，如果节点输入 schema 不是简单 dict，还会绑定一个 `mapper`。

这个 `mapper` 的作用是：

- 把读取出来的 `dict[str, Any]`
- 再还原成节点期望的 schema 类型

例如：

- `TypedDict`
- `Pydantic model`

所以节点函数拿到的 `state` 之所以看起来像一个 TypedDict / 模型对象，是因为 LangGraph 在读完 channels 后又帮你组装了一次。

这意味着：

> **节点看到的是“当前 state 的视图/快照”，不是底层共享对象本身。**

---

## 5. 节点返回值是怎么变成 state 更新的

源码入口：

- `libs/langgraph/langgraph/graph/state.py`
- `CompiledStateGraph.attach_node(...)`
- `_get_updates(...)`
- `libs/langgraph/langgraph/pregel/_write.py`

### 5.1 节点返回的是 partial update

例如一个节点返回：

```python
return {"response": "done", "steps": ["search completed"]}
```

运行时不会把它当作“新 state 全量覆盖”，而是会把它转换成一组更新：

```python
[
    ("response", "done"),
    ("steps", ["search completed"]),
]
```

也就是说，节点输出在内部会被标准化成 `(channel_name, value)` 形式。

### 5.2 写入由 `ChannelWrite` 统一处理

`ChannelWrite` 是 LangGraph 的写入器。

它会把节点返回值组装成写入项，再通过 runtime 注入的 `CONFIG_KEY_SEND` 发给 Pregel。

所以，节点代码虽然只是简单 `return {"x": 1}`，但底层其实走的是：

```text
node output
  -> _get_updates(...)
  -> ChannelWrite
  -> (channel, value) tuples
  -> Pregel apply_writes(...)
```

---

## 6. 真正的数据传递核心：`apply_writes()`

源码入口：

- `libs/langgraph/langgraph/pregel/_algo.py`
- `apply_writes(...)`

这是理解 LangGraph state 传递最关键的函数。

它做了 4 件事：

### 6.1 收集当前 super-step 所有任务的写入

在一个 Pregel step 中，可能有多个节点并行执行。  
每个节点都会产生自己的 writes。

`apply_writes(...)` 先把这些 writes 全部收集起来。

### 6.2 按 channel 分组

例如可能得到：

```python
response: ["done"]
steps: [["a"], ["b"]]
messages: [[msg1], [msg2]]
```

注意这里是“按 channel 聚合后的候选更新值”，还没真正写入。

### 6.3 调用每个 channel 自己的 `update(...)`

这是最核心的一步。

不同 channel 会按自己的规则合并：

- `LastValue.update(vals)`
  - 只能接收一个值
- `BinaryOperatorAggregate.update(vals)`
  - 会按 reducer 依次叠加

也就是说：

> **真正决定 state key 如何合并的，不是节点，不是 graph，而是 channel 自己的 `update(...)` 实现。**

### 6.4 更新 channel 后，触发下一轮节点

如果某个 channel 在这轮被更新且可用，它就可能成为下游节点的 trigger。

于是运行时会在下一轮执行那些依赖这些 channel 的节点。

这也是为什么 LangGraph 的控制流本质上是：

```text
channel 更新
  -> 触发节点
  -> 节点读 channel
  -> 节点写 channel
  -> 再触发下一轮
```

---

## 7. 为什么说 LangGraph 不是“函数串行调用”，而是 Pregel super-step

如果只是普通 Python 编排，通常是：

```text
node_a(state) -> new_state
node_b(new_state) -> newer_state
```

而 LangGraph 更像：

```text
step N:
  一批节点读取当前 channel 快照并执行
  -> 产生 writes
  -> runtime 统一 apply_writes

step N+1:
  下游节点读取更新后的 channel 快照再执行
```

这个差异非常重要，因为它决定了：

- 为什么并发节点可能发生同 key 冲突
- 为什么 reducer 是必要的
- 为什么 `Annotated[..., operator.add]` 这种写法能工作
- 为什么状态持久化天然适合做 checkpoint

---

## 8. 用 `PlanExecute` 例子理解这一点

比如 `plan-and-execute.ipynb` 中的：

```python
class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
```

底层可以近似理解为：

- `input -> LastValue(str)`
- `plan -> LastValue(List[str])`
- `past_steps -> BinaryOperatorAggregate(List[Tuple], operator.add)`
- `response -> LastValue(str)`

所以当 `execute_step(...)` 返回：

```python
{
    "past_steps": [(task, result)]
}
```

它并不是直接把一个大 state dict 传下去，而是：

1. 写入 `past_steps` 这个 channel
2. `past_steps` 的 reducer 用 `operator.add` 合并新值
3. `replan_step(...)` 下一轮读取到新的 `past_steps`

这就是 `state` 在这个 graph 里真正的“传递方式”。

---

## 9. 一句话总结

如果你只记一句话，记这个：

> **LangGraph 中的 state 底层不是直接在节点间传递 dict，而是把 state key 编译成 channels，节点返回 partial updates，Pregel 在 super-step 中通过各个 channel 的 `update()` 规则统一合并后，再把新的 state 快照提供给下一轮节点。**

换一种更工程化的表达：

```text
State 是开发者视角的抽象
Channel 是运行时视角的真实载体
Pregel 是负责读、写、合并、触发下一步的执行引擎
```

---

## 10. 推荐源码阅读顺序

如果你要继续深挖，建议按这个顺序看：

1. `libs/langgraph/langgraph/graph/state.py`
   - 看 `StateGraph`
   - 看 `_get_channels(...)`
   - 看 `compile()`
   - 看 `attach_node(...)`

2. `libs/langgraph/langgraph/channels/last_value.py`
   - 看默认 state key 为什么只能单值更新

3. `libs/langgraph/langgraph/channels/binop.py`
   - 看 reducer 是怎么做聚合的

4. `libs/langgraph/langgraph/pregel/_write.py`
   - 看节点输出怎么变成 channel writes

5. `libs/langgraph/langgraph/pregel/_read.py`
   - 看节点输入怎么从 channel 组装回来

6. `libs/langgraph/langgraph/pregel/_algo.py`
   - 看 `apply_writes(...)`
   - 这是整个状态传递和合并的核心

---

## 11. 面试版回答

如果面试官问：

> LangGraph 中 state 底层是怎么传递的？

你可以直接这样答：

> LangGraph 表面上是 `State -> Partial<State>`，但底层不是直接传 dict。`StateGraph` 编译时会把 state schema 的每个字段转成 channel。节点执行时从 channel 读取当前 state 快照，返回的是 partial update。Pregel runtime 会在每个 super-step 里把所有节点的 writes 收集起来，按 channel 分组，并调用 channel 的 `update()` 方法合并。普通字段默认是 `LastValue`，带 reducer 的字段会变成 `BinaryOperatorAggregate`。合并完成后，再触发下一轮依赖这些 channel 的节点。  

