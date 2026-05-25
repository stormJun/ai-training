# Python 异步与 GIL 基础

这个目录现在合并了原来的：

- `47_asyncio_basics`
- `48_asyncio_primitives_and_gil`

所以主题覆盖两部分：

- asyncio / 协程语法与事件循环基础
- Future / Task / Executor / GIL 基础

整体目标依然不是“大而全”，而是把下面这条学习主线讲清楚：

- 生成器
- `yield from`
- `async` / `await`
- 事件循环
- Future / Task / Executor
- GIL 与绕过方式
- 阻塞 vs 异步 vs 并发

## 目录速览

- `01_asyncio_overview.ipynb`
  - 最早的 notebook 版本材料
- `02_blocking_vs_threadpool_demo.py`
  - 一个很小的“同步 requests”与“线程池并发 requests”对照片段
- `03_io_multiplexing_under_the_hood.py`
  - 用 `selectors`、socket、事件回调去解释 asyncio 底层的 I/O 多路复用思想
- `04_async_syntax_sugar.py`
  - 从生成器协程、`@asyncio.coroutine`、`yield from` 过渡到 `async` / `await`
- `05_await_protocol.py`
  - 解释 `await` 背后的 `__await__()` 协议
- `06_old_style_coroutine.py`
  - 用现代 Python 模拟旧风格 `@coroutine + yield from` 协程写法
- `07_native_coroutine.py`
  - 原生 `async def` + `await` 的并发写法
- `08_logging_debug_demo.py`
  - asyncio 调试日志示例
- `09_slow_callback_debug_demo.py`
  - 慢回调检测示例
- `10_future_demo.py`
  - Future 基础示例
- `11_task_demo.py`
  - Task 基础示例
- `12_executor_demo.py`
  - Executor 基础示例
- `13_gil_demo.py`
  - GIL 基础演示
- `14_bypass_gil_demo.py`
  - 多进程等方式绕过 GIL 的示例
- `pyproject.toml` / `uv.lock` / `uv.toml`
  - 当前目录的依赖与环境管理文件

## 建议学习顺序

推荐按下面顺序看：

1. `04_async_syntax_sugar.py`
2. `05_await_protocol.py`
3. `06_old_style_coroutine.py`
4. `07_native_coroutine.py`
5. `03_io_multiplexing_under_the_hood.py`
6. `02_blocking_vs_threadpool_demo.py`
7. `08_logging_debug_demo.py`
8. `09_slow_callback_debug_demo.py`
9. `10_future_demo.py`
10. `11_task_demo.py`
11. `12_executor_demo.py`
12. `13_gil_demo.py`
13. `14_bypass_gil_demo.py`

这样顺序的逻辑是：

- 先理解协程语法是怎么演进出来的
- 再理解 `await` 协议
- 再看旧/新协程风格的差别
- 再看底层事件循环和 I/O 多路复用
- 最后补 Future / Task / Executor 和 GIL

## 每个文件主要在讲什么

### 1. `04_async_syntax_sugar.py`

这是当前目录里最适合作为入口的文件。

它把协程的演进拆成 3 个阶段：

1. 基于生成器的暂停/恢复
2. `@asyncio.coroutine` + `yield from`
3. `async def` + `await`

如果你想先搞清楚：

- 为什么 `async` / `await` 不是凭空发明的
- 它和生成器到底有什么关系

就从这个文件开始。

### 2. `05_await_protocol.py`

这个文件专门讲一件事：

> `await` 到底在等待什么？

它通过自定义 `__await__()` 来说明：

- 一个对象为什么能被 `await`
- `await` 背后实际上是在消费一个可迭代协议

这是理解协程机制非常关键的一层。

### 3. `06_old_style_coroutine.py`

这个文件保留的是旧风格协程思路：

- `@coroutine`
- `yield from`

虽然现代项目里已经很少这样写，但它有助于理解：

- 原生协程语法是怎么演化过来的
- `yield from` 当年承担了什么角色

### 4. `07_native_coroutine.py`

这是现代写法：

- `async def`
- `await`
- `asyncio.gather`

它是你在真实项目里最常见的基本形式。

这个文件适合用来建立现代 asyncio 的最小心智模型：

```text
定义协程
-> 创建多个任务
-> 并发等待
-> 收集结果
```

### 5. `03_io_multiplexing_under_the_hood.py`

这个文件比前几个更底层。

它重点不是教你写业务代码，而是帮助理解：

- `selectors` 是什么
- 事件循环为什么能管理很多 I/O
- socket 可读事件和回调之间是什么关系

如果你想继续往“原理层”走，这个文件很重要。

### 6. `02_blocking_vs_threadpool_demo.py`

这个文件比较零碎，但它有一个实际价值：

- 展示同步 `requests` 逐个调用
- 再展示 `ThreadPoolExecutor` 并发请求

它可以拿来帮助理解：

- 阻塞式 I/O 的串行问题
- 为什么人们会想走线程池或异步模型

### 7. `08_logging_debug_demo.py` 和 `09_slow_callback_debug_demo.py`

这两个文件聚焦 asyncio 调试：

- 如何看日志
- 如何定位慢回调

适合在你已经能写基础协程之后，再去看“异步程序怎么排查问题”。

### 8. `10_future_demo.py`、`11_task_demo.py`、`12_executor_demo.py`

这三份文件用来补 asyncio 的核心运行单元：

- `Future`
- `Task`
- `Executor`

它们的价值在于帮助你建立更扎实的概念边界：

- `Future` 是结果占位符
- `Task` 是被调度执行的协程包装
- `Executor` 是把阻塞任务扔到线程池/进程池里的桥梁

### 9. `13_gil_demo.py` 和 `14_bypass_gil_demo.py`

这两份文件把主题从“协程”继续延伸到“Python 并发性能边界”：

- GIL 是什么
- 为什么 Python 多线程对 CPU 密集任务帮助有限
- 常见绕过方式为什么是多进程

这部分和 asyncio 不是同一个层次的问题，但放在一起学很有价值，因为它能帮助你判断：

- 什么场景该用协程
- 什么场景该用线程池
- 什么场景该用多进程

## 环境准备

进入目录：

```bash
cd 15_python_concurrency_and_performance/01_asyncio_and_gil_basics
```

安装依赖：

```bash
uv sync --locked
```

如果不用 `uv`，也可以自己按 `pyproject.toml` 里的依赖装。

## 运行方式

当前目录大部分文件都可以直接运行，例如：

```bash
uv run python 04_async_syntax_sugar.py
uv run python 05_await_protocol.py
uv run python 06_old_style_coroutine.py
uv run python 07_native_coroutine.py
uv run python 03_io_multiplexing_under_the_hood.py
uv run python 10_future_demo.py
uv run python 11_task_demo.py
uv run python 12_executor_demo.py
uv run python 13_gil_demo.py
uv run python 14_bypass_gil_demo.py
```

如果你只是想快速看现代协程并发效果，优先跑：

```bash
uv run python 07_native_coroutine.py
```

如果你想先理解 `await` 协议，优先跑：

```bash
uv run python 05_await_protocol.py
```

## 这个目录当前的定位

这个目录现在更适合被理解成：

> asyncio / 协程机制 + Future/Task/Executor + GIL 入门材料

也就是说，它目前最有价值的地方在：

- 帮你把协程语法演进讲清楚
- 帮你把 `await`、事件循环、I/O 多路复用这些概念连起来
- 帮你把 Future / Task / Executor 的边界理清
- 帮你把 GIL 和并发模型的取舍连起来
- 为后续去看 FastAPI、LangGraph、异步数据库、异步 HTTP 请求打基础

## 一句话总结

如果你只选一个文件开始看，就从 [04_async_syntax_sugar.py](/Users/songxijun/workspace/otherProject/ai-training/15_python_concurrency_and_performance/01_asyncio_and_gil_basics/04_async_syntax_sugar.py) 开始；如果你只选一个文件运行，就先跑 [07_native_coroutine.py](/Users/songxijun/workspace/otherProject/ai-training/15_python_concurrency_and_performance/01_asyncio_and_gil_basics/07_native_coroutine.py)。
