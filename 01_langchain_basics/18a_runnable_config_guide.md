# RunnableConfig 使用与源码梳理

这一节专门讲 `RunnableConfig`。

如果说 [18_chain_and_runnable_guide.md](/Users/songxijun/workspace/otherProject/ai-training/01_langchain_basics/18_chain_and_runnable_guide.md) 重点是在解释：

- `Runnable` 是什么
- `prompt | model | parser` 为什么能成立
- `RunnableSequence` / `RunnableParallel` 怎么理解

那么这篇的重点是另一个问题：

- LangChain 运行时配置到底是怎么传进去的？
- `run_name`、`tags`、`metadata`、`callbacks`、`max_concurrency`、`configurable` 分别有什么用？
- 为什么 `Runnable` 源码里到处都是 `config`、`ensure_config`、`merge_configs`、`patch_config`？

可以先用一句话概括：

> `RunnableConfig` 是 LangChain 给所有 Runnable 提供的一层统一运行时控制面板，用来管理 tracing、并发、回调、运行命名、元数据和可配置字段。

参考资料：

- LangChain Reference: https://reference.langchain.com/python/langchain-core/runnables/config
- LangChain API: https://api.python.langchain.com/en/latest/runnables/langchain_core.runnables.config.RunnableConfig.html
- LangChain Docs: https://docs.langchain.com/oss/python/langchain/models

## 一、`RunnableConfig` 是什么

`RunnableConfig` 可以理解成“调用 Runnable 时附带的运行参数字典”。

不是业务输入，不是 prompt 变量，也不是模型输出，而是“这次执行如何运行”的配置。

例如：

```python
result = chain.invoke(
    {"topic": "LangChain"},
    config={
        "run_name": "topic_demo",
        "tags": ["demo", "langchain"],
        "metadata": {"lesson": "18a"},
    },
)
```

这里：

- `{"topic": "LangChain"}` 是业务输入
- `config={...}` 是运行时配置

这两层不要混。

## 二、最常见的字段

官方最常见、最值得先掌握的字段有这些：

### 1. `run_name`

给这次调用取一个运行名，主要用于 tracing / 日志 / 调试。

```python
chain.invoke(
    {"topic": "Runnable"},
    config={"run_name": "runnable_intro_demo"},
)
```

适合：

- 给重要链路命名
- 调试时快速识别这次运行
- 在 LangSmith 或 callback 输出里更好定位

要点：

- 它更偏“这次调用叫什么”
- 通常不会像 `tags` 那样作为长期分类标签使用

### 2. `tags`

给这次调用打标签，而且这些标签会向子调用传播。

```python
chain.invoke(
    {"topic": "Runnable"},
    config={"tags": ["lesson-18a", "demo"]},
)
```

适合：

- 给一批调用打统一标记
- 后续在 tracing 系统中筛选
- 标记实验、版本、环境、任务类型

要点：

- `tags` 会被子 Runnable 继承
- 更适合做分类，而不是做详细业务数据存储

### 3. `metadata`

附加结构化元数据，也会向子调用传播。

```python
chain.invoke(
    {"topic": "Runnable"},
    config={
        "metadata": {
            "course": "ai-training",
            "chapter": "01_langchain_basics",
            "demo": "runnable_config",
        }
    },
)
```

适合：

- 记录用户 ID、课程名、实验名、环境信息
- 给 tracing 留更多上下文
- 做后续日志分析

要点：

- `metadata` 更适合 JSON 风格结构化信息
- 官方建议值尽量可 JSON 序列化

### 4. `callbacks`

给这次调用绑定 callback handler。

```python
chain.invoke(
    {"topic": "Runnable"},
    config={"callbacks": [my_callback_handler]},
)
```

适合：

- 自定义日志打印
- 观察链路中间步骤
- 接 tracing / metrics / 监控系统

从源码角度，它会被转成：

- `CallbackManager`
- `AsyncCallbackManager`

然后在 `on_chain_start` / `on_chain_end` / `on_chain_error` 等生命周期节点里被调用。

### 5. `max_concurrency`

控制批量执行时的最大并发度。

```python
results = chain.batch(
    [{"topic": "A"}, {"topic": "B"}, {"topic": "C"}],
    config={"max_concurrency": 2},
)
```

适合：

- 控制并发压力
- 避免批处理时把下游 API 打爆
- 配合 `batch()` / `abatch()` / `batch_as_completed()` 使用

要点：

- 它不是控制单条 `invoke()` 的速度
- 它主要影响批量或并行场景

### 6. `configurable`

给已经声明为“运行时可配置”的字段传值。

这个字段通常和：

- `.configurable_fields()`
- `.configurable_alternatives()`

配合使用。

例如某个模型先被定义成运行时可切换最大输出 token：

```python
model = model.configurable_fields(...)
```

调用时就可以：

```python
model.invoke(
    "hello",
    config={"configurable": {"output_token_number": 200}},
)
```

这个字段不是拿来放普通 metadata 的，它专门用于“改 Runnable 自己暴露出来的运行时参数”。

### 7. `recursion_limit`

控制 Runnable 嵌套或递归调用的最大深度。

这个字段平时不会像 `tags`、`metadata` 那么常用，但在复杂链、agent 或 `RunnableLambda` 返回 `Runnable` 的场景里很重要。

源码里如果递归层数被耗尽，会直接抛 `RecursionError`。

## 三、两种最常见的使用姿势

### 1. 调用时直接传 `config=...`

这是最直接的方式：

```python
result = chain.invoke(
    {"topic": "LangChain"},
    config={
        "run_name": "langchain_demo",
        "tags": ["demo"],
        "metadata": {"chapter": "18a"},
    },
)
```

适合：

- 单次调用临时指定配置
- 你只想对这一次运行加 tracing 信息

### 2. 先 `.with_config(...)` 再复用

如果某些配置会反复使用，可以先绑定：

```python
configured_chain = chain.with_config(
    {
        "tags": ["course-demo"],
        "metadata": {"chapter": "18a"},
    }
)

configured_chain.invoke({"topic": "Runnable"})
configured_chain.invoke({"topic": "Parser"})
```

这更适合：

- 一组 demo 共用同样 tags / metadata
- 统一绑定 tracing 配置
- 给一条链先预装默认配置

从源码看，这种方式底层通常会返回一个 `RunnableBinding`，不是原对象原地修改。

## 四、在不同执行方式里的表现

### 1. `invoke()` / `ainvoke()`

最基础的单次执行接口，`config` 会直接进入当前 Runnable，并继续向子调用传播。

### 2. `batch()` / `abatch()`

批处理时，LangChain 会先把单个 config 展开成配置列表，或者直接消费你传入的配置列表。

也就是说可以：

```python
chain.batch(inputs, config={"tags": ["batch-demo"]})
```

也可以：

```python
chain.batch(
    inputs,
    config=[
        {"metadata": {"row": 1}},
        {"metadata": {"row": 2}},
        {"metadata": {"row": 3}},
    ],
)
```

这一点在源码里由 `get_config_list()` 负责处理。

### 3. `stream()` / `astream()`

`config` 同样会进入流式执行链路。它不仅影响 tracing，也影响 callback、运行命名和子 run 继承。

### 4. `astream_log()` / `astream_events()`

如果你想观察 Runnable 运行过程中的事件流、chunk 流或中间结果，`config` 也会参与这些 tracing 输出的组织。

尤其：

- `run_name`
- `tags`
- `metadata`
- `callbacks`

都会明显影响你看到的调试信息。

## 五、最容易混淆的点

### 1. `config` 不是 prompt 输入

错误理解：

```python
chain.invoke(
    {"question": "什么是 Runnable"},
    config={"user_id": "123"},
)
```

这里 `user_id` 不会自动进入 prompt 变量，也不会变成模型上下文。它只是运行时配置。

如果你想让模型看到 `user_id`，应该显式进入输入、Prompt 或 middleware，而不是塞进 `config`。

### 2. `metadata` 不是给模型看的

`metadata` 更多是给 tracing、调试、日志和外围系统看的，不是模型上下文。

### 3. `with_config()` 不是修改原对象

它通常返回一个新的包装后的 Runnable。这个思路和：

- `with_retry()`
- `with_listeners()`
- `with_types()`

是一致的。

### 4. `max_concurrency` 主要影响并发执行，不是“让单次调用更快”

它更多是资源控制，而不是性能魔法开关。

## 六、从源码看，`RunnableConfig` 是怎么设计的

前面是使用视角。下面开始看源码设计。

从你贴出来的 `Runnable` 源码和 LangChain `langchain_core.runnables.config` 模块可以提炼出 4 个关键设计点。

### 1. `RunnableConfig` 是统一配置字典，而不是分散参数

LangChain 没有给每个接口单独发明一套：

- `invoke(..., tags=..., callbacks=..., metadata=...)`
- `batch(..., tags=..., callbacks=..., metadata=...)`

而是把它们统一进一个 `config` 字典。

好处是：

- 所有 Runnable 都遵循同一套运行时控制面
- sync / async / batch / stream 都能复用
- 配置可以向下传播

### 2. `ensure_config()`：先把 config 规范化

源码里大量逻辑会先调用：

```python
config = ensure_config(config)
```

它的作用可以理解成：

- 确保 config 一定是一个可用的 dict 结构
- 补齐必要默认值
- 方便后续统一读取

这就是为什么 LangChain 内部很少直接裸用外部传进来的 `config`。

### 3. `merge_configs()` / `patch_config()`：配置不是覆盖，而是逐层合并

这是 `RunnableConfig` 设计里最关键的一点。

LangChain 明确希望配置支持：

- 父链传入一层配置
- 子 Runnable 再补一层配置
- 中间件 / wrapper 再 patch 一层配置

所以它不是简单“替换”，而是合并。

典型场景：

- 父级传 `tags=["parent"]`
- 子级再加 `tags=["child"]`
- 最终保留继承和叠加效果

这也是 reference 文档里特别强调的点：`RunnableConfig` 是 `total=False` 的 TypedDict，故意允许“部分配置先创建，再逐层 merge”。

### 4. callback / tracing 是通过 config 传播的

从源码看，`invoke()`、`ainvoke()`、`batch()`、`stream()` 等逻辑里，都会通过：

- `get_callback_manager_for_config`
- `get_async_callback_manager_for_config`
- `patch_config(..., callbacks=run_manager.get_child())`

把父 run 的回调上下文传给子 run。

这说明 `RunnableConfig` 不只是“用户传的可选参数”，而是 LangChain 内部管理父子 run 生命周期的重要通道。

## 七、`RunnableSequence` 怎么消费 `RunnableConfig`

`RunnableSequence` 的核心逻辑是：

1. 根 run 先启动
2. 每一步 step 都拿到一份 patch 过的 child config
3. 每个 step 的 callbacks 都挂到父 run 的 child 上
4. 每一步的输出再传给下一步

你贴的源码里，关键形式就是：

```python
config = patch_config(
    config, callbacks=run_manager.get_child(f"seq:step:{i + 1}")
)
```

这意味着：

- 每个 step 都不是孤立运行
- 它们共享同一条根调用链，但各自有独立 child run
- tracing 系统因此能看到完整的父子树

这也是为什么一个 `prompt | model | parser` 在 tracing 里能展开成多层步骤，而不是只看到一个黑盒调用。

## 八、`RunnableParallel` 怎么消费 `RunnableConfig`

并行场景下，思路类似，但变成：

- 同一个根 run
- 多个并行子分支
- 每个分支都拿到自己的 child callback 配置

你贴的源码里，关键形式是：

```python
callbacks=run_manager.get_child(f"map:key:{key}")
```

这让并行分支在 tracing 里也能被清楚区分。

所以 `RunnableConfig` 在串行和并行里的角色很一致：

- 根 run 统一启动
- 子 run 通过 patched config 继承上下文

## 九、默认 `ainvoke()` / `batch()` 为什么也要吃 config

这部分在源码里非常清楚：

- `ainvoke()` 默认用线程池包装同步 `invoke()`
- `batch()` 默认用线程池并发跑多个 `invoke()`
- `abatch()` 默认用 `asyncio.gather`

即便只是“默认实现”，也必须接收 `config`，因为：

1. tracing 不能丢
2. callbacks 不能丢
3. `max_concurrency` 不能丢
4. 子调用上下文不能丢

也就是说，`config` 并不是“高级功能才用到的附加参数”，它其实已经被 LangChain 放在执行模型的主路径上了。

## 十、`with_config()` 在源码里的真正含义

从源码看，`with_config()` 常见落点是返回一个 `RunnableBinding`：

- 原 Runnable 保持不变
- 新对象包住旧对象
- 在执行时先合并绑定配置，再把调用委托给底层 Runnable

这和很多框架里的 decorator / wrapper 思路是一样的。

所以 `with_config()` 本质不是“设置属性”，而是：

> 构造一个带默认运行时配置的新 Runnable 包装器

这也是为什么它能和：

- `with_retry()`
- `with_listeners()`
- `with_types()`

形成一致的 API 风格。

## 十一、从设计上怎么理解 `RunnableConfig`

可以把 LangChain 的这套设计总结成一句话：

> `RunnableConfig` 不是业务数据，而是 Runnable 执行环境的统一控制面。

它在框架中的作用类似于：

- tracing 上下文
- 回调上下文
- 并发策略
- 运行命名
- 运行时可配置参数容器

所以它既服务用户代码，也服务 LangChain 框架内部。

## 十二、推荐掌握顺序

如果你第一次系统理解 `RunnableConfig`，建议按这个顺序掌握：

1. 先会在 `invoke(..., config=...)` 里使用：
   - `run_name`
   - `tags`
   - `metadata`
2. 再理解：
   - `callbacks`
   - `max_concurrency`
3. 再理解：
   - `with_config(...)`
   - `configurable`
4. 最后再看源码里的：
   - `ensure_config`
   - `merge_configs`
   - `patch_config`
   - child callback propagation

这样会比较顺。

## 十三、一句话总结

`RunnableConfig` 是 LangChain Runnable 体系的统一运行时配置协议。

对业务代码来说，它让你能控制 tracing、并发、回调和运行时参数；对源码设计来说，它让 `RunnableSequence`、`RunnableParallel`、`RunnableBinding` 和 callback 系统都能在同一套执行上下文里协作。

如果你想继续看“这些设计在真实 agent 系统里是怎么被使用的”，建议接着读：

- [18b_deerflow_runnable_design.md](/Users/songxijun/workspace/otherProject/ai-training/01_langchain_basics/18b_deerflow_runnable_design.md)
  - 结合 DeerFlow 工程代码，说明 `RunnableConfig`、`astream()`、`get_config()`、`with_config()`、`RunnableBinding` 在真实运行链中的落点
