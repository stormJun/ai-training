# Python 异步并发 - Python 高性能编程与异步并发完全指南

> 本文档是 AI 工程师训练营 Python 异步并发 的完整总结，涵盖 Python 异步编程、并发模式、高性能 API 设计、LangChain/LangGraph 异步工作流、GPU 加速等核心主题。

---

## 目录

- [第一部分：协程与事件循环基础](#第一部分协程与事件循环基础)
  - [1.1 底层 I/O 多路复用机制](#11-底层-io-多路复用机制)
  - [1.2 自定义 Awaitable 对象](#12-自定义-awaitable-对象)
  - [1.3 异步调试与日志](#13-异步调试与日志)
  - [1.4 async/await 状态机与实践](#14-asyncawait-状态机与实践)
- [第二部分：Future、Task 与 Executor](#第二部分futuretask-与-executor)
  - [2.1 Future 对象与回调](#21-future-对象与回调)
  - [2.2 Task 并发执行](#22-task-并发执行)
  - [2.3 Executor 集成](#23-executor-集成)
  - [2.4 协程与线程上下文切换开销](#24-协程与线程上下文切换开销)
- [第三部分：GIL 与多线程/多进程](#第三部分gil-与多线程多进程)
  - [3.1 GIL 对性能的影响](#31-gil-对性能的影响)
  - [3.2 异步 I/O 实现](#32-异步-io-实现)
  - [3.3 综合性能测试](#33-综合性能测试)
- [第四部分：多进程与协程混合架构](#第四部分多进程与协程混合架构)
  - [4.1 任务调度器设计](#41-任务调度器设计)
  - [4.2 进程池工厂模式](#42-进程池工厂模式)
  - [4.3 混合任务场景](#43-混合任务场景)
  - [4.4 混合架构设计守则](#44-混合架构设计守则)
- [第五部分：高并发 API 最佳实践](#第五部分高并发-api-最佳实践)
  - [5.1 RESTful API 设计](#51-restful-api-设计)
  - [5.2 WebSocket 与实时通信](#52-websocket-与实时通信)
  - [5.3 数据库连接池](#53-数据库连接池)
  - [5.4 速率限制与缓存](#54-速率限制与缓存)
- [第六部分：LangChain/LangGraph 异步工作流](#第六部分langchainlanggraph-异步工作流)
  - [6.1 LangChain 异步 API](#61-langchain-异步-api)
  - [6.2 LangGraph 异步节点](#62-langgraph-异步节点)
  - [6.3 重试与超时机制](#63-重试与超时机制)
  - [6.4 自定义回调处理器](#64-自定义回调处理器)
- [第七部分：GPU 加速与向量检索](#第七部分gpu-加速与向量检索)
  - [7.1 FAISS GPU 索引](#71-faiss-gpu-索引)
  - [7.2 异步向量搜索](#72-异步向量搜索)
- [第八部分：性能分析与优化](#第八部分性能分析与优化)
  - [8.1 性能基准测试](#81-性能基准测试)
  - [8.2 Profiling 工具](#82-profiling-工具)
  - [8.3 最佳实践总结](#83-最佳实践总结)

---

# 第一部分：协程与事件循环基础

## 1.1 底层 I/O 多路复用机制

### 核心概念

Python `asyncio` 的事件循环底层依赖操作系统的 I/O 多路复用机制：
- **Linux**: `epoll`
- **macOS/BSD**: `kqueue`
- **Windows**: `select` (IOCP 支持有限)

Python 通过 `selectors` 模块提供统一接口。

### EventLoopIntegration 实现

**文件**: `p5_底层IO多路复用过程.py`

```python
import selectors
import asyncio

class EventLoopIntegration:
    """演示 asyncio 与底层 selector 的集成"""

    def __init__(self):
        # 创建 selector (自动选择最优实现)
        self.selector = selectors.DefaultSelector()
        self._fd_to_callback = {}
        self._stop = False

    def register_reader(self, fd, callback):
        """注册文件描述符的读事件"""
        key = self.selector.register(fd, selectors.EVENT_READ, data=callback)
        self._fd_to_callback[fd] = callback

    def _poll_for_events(self, timeout=None):
        """核心事件循环机制"""
        # 等待 I/O 事件
        events = self.selector.select(timeout)

        # 处理就绪的事件
        for key, mask in events:
            callback = self._fd_to_callback[key.fd]
            callback()  # 恢复协程执行

    def run_until_complete(self, coro):
        """运行协程直到完成"""
        task = asyncio.create_task(coro)

        while not task.done():
            self._poll_for_events(timeout=0.01)

        return task.result()
```

**关键点**:
- `selector.select()` 是**阻塞调用**，等待任意注册的 fd 就绪
- 当 socket 数据到达时，`epoll` 通知事件循环
- 事件循环调用关联的回调函数，恢复协程执行

---

### selector 的作用

```
┌──────────────────────────────────────────┐
│         Python Event Loop                │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │  selector.select(timeout)          │  │
│  │  等待任意 fd 就绪                    │  │
│  └────────────┬───────────────────────┘  │
│               │                           │
│               ▼                           │
│  ┌────────────────────────────────────┐  │
│  │  events = [(fd1, READ), (fd2, ...)]│  │
│  └────────────┬───────────────────────┘  │
│               │                           │
│               ▼                           │
│  ┌────────────────────────────────────┐  │
│  │  for fd, mask in events:           │  │
│  │      callback = fd_map[fd]         │  │
│  │      callback()  ← 恢复协程         │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────┐
│         Operating System                 │
│  epoll/kqueue/select                     │
│  监控多个 socket 文件描述符               │
└──────────────────────────────────────────┘
```

### 事件循环职责与阶段

- 职责：调度/恢复协程、处理网络 I/O、管理子进程与定时任务，是异步程序的“单线程心脏”
- 三阶段：任务注册 → I/O 多路复用等待就绪 → 回调执行/恢复协程
- 特点：单线程协作式调度，避免线程上下文切换；如果在回调里做 CPU 密集运算会堵塞后续事件
- 典型场景：高并发 Web 服务、数据库/HTTP I/O 密集流水线、实时推送

**工程经验速记**:
- 事件循环中避免任何阻塞操作（同步 I/O、长时间计算）；必要时移交到 executor
- 设置 `uvloop`（非 Windows）可获得更快网络 I/O；启用 `debug=True` 或 `PYTHONASYNCIODEBUG=1` 排查协程泄漏/未 awaited
- 对外暴露 API 时，决定同步/异步边界：内部保持全异步，边界用 executor 适配遗留同步代码

---

## 1.2 自定义 Awaitable 对象

### `__await__` 协议

**文件**: `p7_await方法.py`

```python
class CustomAwaitable:
    """自定义可等待对象"""

    def __init__(self, value):
        self.value = value

    def __await__(self):
        """
        __await__ 必须返回一个生成器
        yield 表示让出控制权给事件循环
        """
        print(f"准备解析值: {self.value}")
        yield  # 让出控制权
        print(f"值已解析: {self.value}")
        return self.value  # 返回 await 表达式的结果

# 使用
async def main():
    result = await CustomAwaitable(42)
    print(f"最终结果: {result}")

# 输出:
# 准备解析值: 42
# 值已解析: 42
# 最终结果: 42
```

**执行流程**:
1. `await CustomAwaitable(42)` 调用 `__await__()`
2. 执行到 `yield` 时，控制权返回事件循环
3. 事件循环在下一次迭代中恢复生成器
4. `return self.value` 成为 `await` 表达式的值

---

## 1.3 异步调试与日志

### 结构化日志配置

**文件**: `p11_1日志调试代码.py`

```python
import logging
import asyncio

# 配置 DEBUG 级别日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

async def async_task(task_id: int):
    """带日志的异步任务"""
    logger.debug(f"任务 {task_id} 开始")
    await asyncio.sleep(0.1)
    logger.debug(f"任务 {task_id} 完成")
    return f"Result-{task_id}"

async def main():
    tasks = [async_task(i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    logger.info(f"所有任务完成: {results}")

# 输出示例:
# 2025-12-15 10:23:45 [DEBUG] __main__ - 任务 0 开始
# 2025-12-15 10:23:45 [DEBUG] __main__ - 任务 1 开始
# ...
# 2025-12-15 10:23:45 [DEBUG] __main__ - 任务 0 完成
# 2025-12-15 10:23:45 [INFO] __main__ - 所有任务完成: ['Result-0', ...]
```

**最佳实践**:
- 为每个任务添加唯一 ID
- 记录任务开始/完成时间
- 捕获异常并记录 traceback
- `asyncio.run(main(), debug=True)` 或环境变量开启 debug；配合 `loop.set_exception_handler` 统一处理未捕获异常
- 对需要追踪的 Task 记录创建栈，生产排障时定位悬空任务或未 awaited 协程


## 1.4 async/await 状态机与实践

### 状态机原理

- `async/await` 是协程状态机的语法糖：`await obj` → 调用 `obj.__await__()`，事件循环驱动迭代器挂起/恢复
- 本质等价于生成器的 `yield from` 委托，但原生协程在语义和调度上更清晰，避免误用

**演进简表**:
| 版本 | 特性 | 说明 |
|------|------|------|
| 2.2  | `yield` | 只能产出值 |
| 3.3  | `yield from` | 委托子生成器，首次具备可组合性 |
| 3.5  | `async`/`await` | 原生协程语法，事件循环友好 |

### 何时使用 async/await
- **推荐**: 网络 I/O（HTTP/WebSocket）、数据库操作、文件 I/O (aiofiles) 等 I/O 密集场景
- **避免**: 纯 CPU 密集任务，除非配合 `ProcessPoolExecutor` 或 C 扩展释放 GIL
- 设计 API 时优先保持接口异步；无法改写的同步库可用线程池桥接

### 错误与超时模式

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

async def robust_operation():
    try:
        async with asyncio.timeout(10):  # 超时控制
            return await risky_task()
    except asyncio.TimeoutError:
        logger.warning("操作超时，使用兜底值")
        return DEFAULT_VALUE
    except RecoverableError as exc:
        logger.info("可重试错误，抛给上层处理")
        raise exc
    except Exception:
        logger.exception("未预期错误")
        return None
```

### 调试建议
- 启用事件循环调试：`PYTHONASYNCIODEBUG=1` 或 `asyncio.run(main(), debug=True)`
- 统一在任务名中加入上下文信息（用户/请求 ID），便于日志排查
- 小心“忘记 await”造成的悬空任务；必要时使用 `asyncio.TaskGroup` 保证结构化并发

---

# 第二部分：Future、Task 与 Executor

## 2.1 Future 对象与回调

### Future 基础

**文件**: `p12_1Future.py`

```python
import asyncio

async def basic_future_example():
    """Future 对象演示"""
    loop = asyncio.get_event_loop()

    # 创建 Future
    future = loop.create_future()

    # 添加回调
    def callback_example(fut):
        print(f"Future 完成，结果: {fut.result()}")

    future.add_done_callback(callback_example)

    # 模拟异步数据到达
    def on_data_received(data):
        future.set_result(f"接收到数据: {data}")

    # 0.1 秒后设置结果
    loop.call_later(0.1, on_data_received, "Hello World")

    # 等待 Future 完成
    result = await future
    return result

# 运行
asyncio.run(basic_future_example())
# 输出:
# Future 完成，结果: 接收到数据: Hello World
```

**关键概念**:
- `Future` 表示**未来会有的结果**
- `set_result()` 设置结果，触发所有回调
- `await future` 等待结果就绪

**工程经验速记**:
- Future 多由框架/底层创建，业务层更多直接用 Task；只有在回调式 API 与协程桥接时需要自己造 Future
- `add_done_callback` 内避免阻塞操作，必要时再投递回事件循环 (`loop.call_soon`)；回调里处理异常 `fut.exception()`
- 取消要么向上冒泡 `CancelledError`，要么在回调里做清理并重新抛出，避免悄悄吞掉

---

## 2.2 Task 并发执行

### asyncio.create_task()

**文件**: `p12_2Task.py`

```python
import asyncio

async def quick_task(name: str, duration: float):
    """模拟耗时任务"""
    print(f"任务 {name} 开始 (耗时 {duration}s)")
    await asyncio.sleep(duration)
    print(f"任务 {name} 完成")
    return f"{name}-result"

async def demonstrate_create_task():
    """演示 Task 并发"""
    # 创建多个并发任务
    task_a = asyncio.create_task(quick_task("A", 1.0))
    task_b = asyncio.create_task(quick_task("B", 2.0))
    task_c = asyncio.create_task(quick_task("C", 1.5))

    # 并发执行
    results = await asyncio.gather(task_a, task_b, task_c)
    return results

# 运行
asyncio.run(demonstrate_create_task())
# 输出 (几乎同时开始):
# 任务 A 开始 (耗时 1.0s)
# 任务 B 开始 (耗时 2.0s)
# 任务 C 开始 (耗时 1.5s)
# 任务 A 完成  (1秒后)
# 任务 C 完成  (1.5秒后)
# 任务 B 完成  (2秒后)
```

**关键点**:
- `create_task()` 立即调度任务到事件循环
- 任务**并发**执行，不是串行
- 总耗时 ≈ `max(durations)` 而非 `sum(durations)`

**工程经验速记**:
- 3.11+ 优先用 `asyncio.TaskGroup` 管理一组任务，退出时统一取消，避免悬空任务
- `asyncio.gather(..., return_exceptions=True)` 适合“批量请求容错”场景；默认行为遇到首个异常会取消其余
- 给关键任务命名 (`name=`) 方便日志/诊断；在关闭流程里显式 `task.cancel()` 并 `await task`

---

## 2.3 Executor 集成

### ThreadPoolExecutor 与 asyncio

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

def blocking_io_operation(url: str):
    """阻塞式 I/O 操作 (例如同步 HTTP 请求)"""
    import requests
    response = requests.get(url)
    return response.status_code

async def async_wrapper():
    """在 asyncio 中调用同步函数"""
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=4)

    # 使用 executor 运行阻塞函数
    result = await loop.run_in_executor(
        executor,
        blocking_io_operation,
        "https://httpbin.org/get"
    )

    return result
```

**适用场景**:
- 无法改写的同步库 (如 `requests`)
- CPU 密集型任务 (使用 `ProcessPoolExecutor`)

**工程经验速记**:
- I/O 阻塞用线程池；CPU 密集用进程池，避免线程争抢 GIL
- 池大小：线程池与 I/O 并发/外部连接上限匹配；进程池与 CPU 核数匹配
- 线程池任务里不要再调用协程；进程池参数保持可序列化，避免闭包/大对象导致 pickle 开销

---

## 2.4 协程与线程上下文切换开销

**来源**: PDF 性能对比实验

| 开销类型 | 协程 | 线程 |
|---------|------|------|
| 上下文切换 | ~50ns (用户态保存栈) | ~1000ns (进入内核态) |
| 内存占用 | ~2KB/协程 | ~8MB/线程 |
| 调度模型 | 协作式、事件循环驱动 | 抢占式、OS 调度 |

**结论**:
- 同一台机器上可以安全地管理成千上万协程而不会爆内存
- 多线程在 I/O 场景下仍可用，但调度和上下文切换开销更高
- CPU 密集场景应避免多线程抢占 GIL，而改用多进程或 C 扩展

---

# 第三部分：GIL 与多线程/多进程

## 3.1 GIL 对性能的影响

### GIL (Global Interpreter Lock)

**文件**: `p16_1GIL.py`

**核心概念**:
- CPython 解释器的**全局互斥锁**
- **同一时刻仅允许一个线程执行 Python 字节码**
- I/O 密集型任务不受影响 (I/O 期间释放 GIL)
- CPU 密集型任务受严重限制 (多线程无法利用多核)

### GIL 释放机制
- **被动释放**: 线程遇到阻塞 I/O (`socket.recv`, 文件读写、`time.sleep`) 或系统调用时，解释器自动释放 GIL
- **显式让出**: `asyncio.sleep(0)`/`await` 等挂起点会触发调度，让其他任务获得执行机会
- **C 扩展释放**: NumPy、PyTorch 等在进入耗时 C 函数时主动释放 GIL，允许真正的多线程并行
- **注意**: 进入 C 扩展前释放，返回 Python 层时重新获取；纯 Python CPU 密集代码无法绕过 GIL

### 常见“绕过/释放 GIL”的库与方式
- 数值/科学计算: `numpy`、`scipy`、`pandas`（底层 C/Fortran 运算释放 GIL），`numba` JIT 后的并行区域
- 深度学习: `torch`、`tensorflow`（C++/CUDA 内核多线程并行）
- 多媒体/图像: `opencv-python`、`Pillow` 部分 C 扩展
- 自定义 C 扩展: Cython 可用 `with nogil:` 包裹耗时循环；手写 C 扩展用 `Py_BEGIN_ALLOW_THREADS`/`Py_END_ALLOW_THREADS`
- 进程外并行: `multiprocessing`、`ProcessPoolExecutor` 通过多进程规避 GIL

### GIL 影响实验

```python
import time
import threading

def cpu_bound_task(n):
    """CPU 密集型任务"""
    result = 0
    for i in range(n):
        result += i ** 2
    return result

def io_bound_task(duration):
    """I/O 密集型任务"""
    time.sleep(duration)
    return "Done"

# 实验 1: CPU 密集型 + 多线程
threads = []
for _ in range(4):
    t = threading.Thread(target=cpu_bound_task, args=(10_000_000,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
# 结果: 耗时 ≈ 单线程耗时 (GIL 限制)

# 实验 2: I/O 密集型 + 多线程
threads = []
for _ in range(4):
    t = threading.Thread(target=io_bound_task, args=(1.0,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
# 结果: 耗时 ≈ 1秒 (真正并发，GIL 在 I/O 时释放)
```

**结论**:
| 任务类型 | 多线程加速比 | 推荐方案 |
|---------|-------------|---------|
| **CPU 密集** | ~1.0x | `multiprocessing` (多进程) |
| **I/O 密集** | ~Nx (N=线程数) | `asyncio` / 多线程 |

### 工程经验速记
- 先量化再决策：用 `cProfile`/`py-spy` 判断瓶颈是 I/O 还是 CPU，再选 asyncio/线程池/进程池
- 同步库桥接：无法改写的阻塞 I/O 用 `ThreadPoolExecutor`；CPU 密集统一放 `ProcessPoolExecutor`
- 线程数 ≠ 越多越好：线程池设置为“CPU 核数或略多”，避免上下文切换放大；进程池注意内存占用
- 优先向量化/批处理：数值/ML 场景先尝试 NumPy/torch 的矢量化或批量接口，往往比多进程更快更省内存
- 避免阻塞事件循环：在 `async` 代码里调用同步重计算或阻塞 I/O 必须包在 `run_in_executor`，否则整个 loop 被卡死
- 多进程 + 协程：每个进程独立创建事件循环和资源，不要跨进程共享 session/连接

---

## 3.2 异步 I/O 实现

### aiohttp 异步 HTTP 请求

**文件**: `p17_3async.py`

```python
import asyncio
import aiohttp

class AsynchronousImplementation:
    """异步实现 (aiohttp)"""

    async def create_session(self):
        """创建共享 session"""
        return aiohttp.ClientSession()

    async def async_http_request(self, session, task_id: int):
        """异步 HTTP 请求"""
        url = "https://httpbin.org/delay/1"

        try:
            async with session.get(url) as response:
                data = await response.json()
                return {
                    'task_id': task_id,
                    'status_code': response.status,
                    'data': data
                }
        except Exception as e:
            return {'task_id': task_id, 'error': str(e)}

    async def run_streaming_tasks(self, duration: float = 10.0):
        """并发流式任务 (限制并发数)"""
        session = await self.create_session()
        semaphore = asyncio.Semaphore(4)  # 最多 4 个并发请求

        async def bounded_task(tid: int):
            async with semaphore:
                return await self.async_http_request(session, tid)

        start_time = asyncio.get_event_loop().time()
        tasks = []
        task_id = 0

        while asyncio.get_event_loop().time() - start_time < duration:
            task = asyncio.create_task(bounded_task(task_id))
            tasks.append(task)
            task_id += 1
            await asyncio.sleep(0.1)

        results = await asyncio.gather(*tasks)
        await session.close()

        return results
```

**关键点**:
- `Semaphore(4)` 限制并发数为 4
- 共享 `ClientSession` 复用 TCP 连接
- `await asyncio.sleep()` 不阻塞事件循环

**工程经验速记**:
- 共享 `ClientSession`/连接器，避免频繁建连；设置 `limit`/`limit_per_host` 控制并发
- 外部接口要设超时与重试（区分幂等/非幂等）；超时用 `timeout=aiohttp.ClientTimeout(total=...)`
- 对高并发任务使用信号量/队列做背压，防止瞬时创建过多协程耗尽内存或连接

---

## 3.3 综合性能测试

### 四种并发模式对比

**文件**: `p18_1IO密集场景综合性能测试.py`

```python
import time
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# 1. 同步实现 (基线)
def synchronous_http(url):
    import requests
    return requests.get(url).status_code

def test_synchronous(num_requests=50):
    start = time.time()
    for _ in range(num_requests):
        synchronous_http("https://httpbin.org/get")
    return time.time() - start

# 2. 异步实现 (asyncio + aiohttp)
async def async_http(session, url):
    async with session.get(url) as resp:
        return resp.status

async def test_async(num_requests=50):
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [async_http(session, "https://httpbin.org/get")
                 for _ in range(num_requests)]
        await asyncio.gather(*tasks)
    return time.time() - start

# 3. 多线程实现
def test_multithreading(num_requests=50):
    start = time.time()
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(synchronous_http, "https://httpbin.org/get")
                   for _ in range(num_requests)]
        for future in futures:
            future.result()
    return time.time() - start

# 4. 多进程实现
def test_multiprocessing(num_requests=50):
    start = time.time()
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(synchronous_http, "https://httpbin.org/get")
                   for _ in range(num_requests)]
        for future in futures:
            future.result()
    return time.time() - start

# 性能对比 (50 个 HTTP 请求)
print(f"同步: {test_synchronous():.2f}s")  # ~50s (串行)
print(f"异步: {asyncio.run(test_async()):.2f}s")  # ~1s (并发)
print(f"多线程: {test_multithreading():.2f}s")  # ~2s (受 GIL 影响)
print(f"多进程: {test_multiprocessing():.2f}s")  # ~3s (进程开销大)
```

**性能结论**:
```
I/O 密集型任务性能排名:
1. 异步 (asyncio)      - 最快  ✅
2. 多线程              - 次快
3. 多进程              - 较慢 (进程创建开销)
4. 同步                - 最慢

**工程经验速记**:
- 基准时分清瓶颈：I/O 场景优先 async；CPU 场景用多进程或向量化；混合场景拆分执行
- 线程池与 async 组合时，线程池大小与外部服务限流/连接池匹配，避免自身制造排队放大延迟
- 在真实网络/数据库环境压测，关注 P95/P99，而不仅是平均耗时
```

---

# 第四部分：多进程与协程混合架构

## 4.1 任务调度器设计

### TaskScheduler 架构

**文件**: `p21_多进程与协程混合/main.py`, `scheduler.py`

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict, Any

class TaskScheduler:
    """
    混合任务调度器
    - CPU 密集型 → 多进程
    - I/O 密集型 → 协程
    """

    def __init__(self, pool_factory):
        self.pool_factory = pool_factory
        self.process_pool = None

    def initialize(self, max_workers=4):
        """初始化进程池"""
        self.process_pool = ProcessPoolExecutor(max_workers=max_workers)

    async def schedule_task(self, task: Dict[str, Any]):
        """调度单个任务"""
        task_type = task.get('type')

        if task_type == 'cpu':
            # CPU 密集型 → 进程池
            return await self._schedule_cpu_task(task)
        elif task_type == 'io':
            # I/O 密集型 → 协程
            return await self._schedule_io_task(task)
        else:
            return {'status': 'failed', 'error': 'Unknown task type'}

    async def _schedule_cpu_task(self, task: Dict[str, Any]):
        """CPU 任务 → 进程池"""
        loop = asyncio.get_running_loop()

        # 在进程池中执行
        result = await loop.run_in_executor(
            self.process_pool,
            cpu_worker,  # 独立进程中的函数
            task
        )
        return result

    async def _schedule_io_task(self, task: Dict[str, Any]):
        """I/O 任务 → 协程"""
        # 直接在当前事件循环中执行
        return await io_worker_async(task)

    async def schedule_tasks(self, tasks: List[Dict[str, Any]]):
        """批量调度任务"""
        task_coroutines = [self.schedule_task(t) for t in tasks]
        return await asyncio.gather(*task_coroutines)

    def shutdown(self):
        """关闭进程池"""
        if self.process_pool:
            self.process_pool.shutdown(wait=True)

# CPU 工作函数 (在独立进程中执行)
def cpu_worker(task):
    """CPU 密集型任务处理器"""
    operation = task.get('operation')
    data = task.get('data')

    if operation == 'fibonacci':
        result = fibonacci(data)
        return {'status': 'completed', 'result': result}
    elif operation == 'data_analysis':
        result = sum(data) / len(data)
        return {'status': 'completed', 'result': result}
    else:
        # 默认: 复杂计算
        result = sum(x ** 2 for x in data)
        return {'status': 'completed', 'result': result}

# I/O 工作函数 (协程)
async def io_worker_async(task):
    """I/O 密集型任务处理器"""
    import aiohttp

    url = task.get('url')
    method = task.get('method', 'GET')

    async with aiohttp.ClientSession() as session:
        if method == 'GET':
            async with session.get(url) as resp:
                return {
                    'status': 'completed',
                    'status_code': resp.status,
                    'data': await resp.text()
                }
```

---

## 4.2 进程池工厂模式

### ProcessPoolFactory

**文件**: `p21_多进程与协程混合/factories.py`

```python
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

class ProcessPoolFactory:
    """进程池工厂 (单例模式)"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pool = None
        return cls._instance

    def create_pool(self, max_workers=None):
        """创建进程池"""
        if max_workers is None:
            max_workers = mp.cpu_count()

        self._pool = ProcessPoolExecutor(max_workers=max_workers)
        return self._pool

    def get_pool(self):
        """获取现有进程池"""
        if self._pool is None:
            return self.create_pool()
        return self._pool

    def shutdown_pool(self):
        """关闭进程池"""
        if self._pool:
            self._pool.shutdown(wait=True)
            self._pool = None
```

---

## 4.3 混合任务场景

### 实战示例：爬虫 + 数据处理

**文件**: `p21_多进程与协程混合/main.py`

```python
async def run_practical_scenario():
    """
    混合任务场景:
    - HTTP 请求 (I/O 密集) → 协程
    - 数据分析 (CPU 密集) → 多进程
    """
    scheduler = TaskScheduler(ProcessPoolFactory())
    scheduler.initialize(max_workers=4)

    tasks = []

    # 1. 网站爬取任务 (I/O)
    for i in range(4):
        tasks.append({
            'id': f'http-{i}',
            'type': 'io',
            'url': f'https://httpbin.org/get',
            'method': 'GET'
        })

    # 2. 数据处理任务 (CPU)
    import random
    test_data = [random.randint(1, 1000) for _ in range(500_000)]

    tasks.append({
        'id': 'cpu-analysis',
        'type': 'cpu',
        'operation': 'data_analysis',
        'data': test_data
    })

    # 3. 斐波那契计算 (CPU)
    for i in range(3):
        tasks.append({
            'id': f'cpu-fib-{i}',
            'type': 'cpu',
            'operation': 'fibonacci',
            'data': 50 + i
        })

    # 执行所有任务 (并发)
    start_time = time.time()
    results = await scheduler.schedule_tasks(tasks)
    total_time = time.time() - start_time

    print(f"总耗时: {total_time:.2f}秒")
    print(f"完成任务: {len([r for r in results if r['status'] == 'completed'])}/{len(tasks)}")

    scheduler.shutdown()
    return results

# 运行
asyncio.run(run_practical_scenario())
```

**性能优势**:
- I/O 任务并发执行 (协程)
- CPU 任务并行执行 (多进程)
- 充分利用系统资源

**工程经验速记**:
- 混合架构先拆分任务类型；任务描述里携带 `type`/幂等性/重试策略，调度层只做路由
- 进程池初始化要在 `if __name__ == "__main__":` 保护下，避免 Windows/fork 问题
- 进程内资源懒加载（如 DB 连接、LLM 客户端），避免 fork 后共享句柄
- 对批量任务用队列 + backpressure 控制提交速率，避免一次性提交巨量任务拉爆内存

## 4.4 混合架构设计守则

- 每个进程维护自己的事件循环，避免跨进程共享 loop 对象
- 进程间通信使用队列/管道传递消息，避免共享数据库连接等有状态资源
- 资源 (HTTP session、DB 连接、缓存客户端) 在各进程内独立创建与关闭
- 在类 Unix 环境可启用 `uvloop` 提升异步 I/O 性能（Windows 不支持）
- 监控与调优：跟踪进程池队列长度、事件循环滞后、CPU/内存占用，防止单点被压垮

---

# 第五部分：高并发 API 最佳实践

## 5.1 RESTful API 设计

### FastAPI 异步路由

**目录**: `3/p24`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

# 异步路由
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    """异步查询数据库"""
    await asyncio.sleep(0.1)  # 模拟数据库查询
    return {"item_id": item_id, "name": "Sample Item"}

@app.post("/items/")
async def create_item(item: Item):
    """异步创建资源"""
    # Pydantic 自动验证
    await save_to_database(item)
    return {"id": 123, **item.dict()}
```

**最佳实践**:
- 所有 I/O 操作使用 `async def`
- 使用 Pydantic 模型验证
- 合理使用 HTTP 状态码

### 设计要点
- 资源化 URI：`/users/{id}/orders` 等面向资源的路径，不用动词
- HTTP 方法语义：`GET` 查询、`POST` 创建、`PUT/PATCH` 更新、`DELETE` 删除，避免语义漂移
- 无状态性：请求携带全部上下文（认证、租户、幂等键），便于水平扩容
- 版本管理：`/v1/` 或 `Accept-Version`，在大版本升级时避免破坏旧客户端
- 错误处理：统一错误响应格式，4xx/5xx 区分客户端 vs 服务端问题
- 安全性：最小权限访问控制，避免在日志中泄露敏感数据

**工程经验速记**:
- FastAPI 路由尽量保持 `async def`，避免隐式阻塞；若必须同步，包一层 `run_in_executor`
- 模型校验错误走统一异常处理器，返回一致的错误码/结构；在中间件里记录 trace_id/用户/租户
- 幂等接口提供幂等键（如 `Idempotency-Key`），配合缓存/DB 保障重复提交安全

---

## 5.2 WebSocket 与实时通信

### FastAPI WebSocket

**目录**: `3/p26`

```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接"""
    await websocket.accept()

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            # 调用 LLM (流式返回)
            async for chunk in llm_stream(data):
                await websocket.send_text(chunk)

    except WebSocketDisconnect:
        print("客户端断开连接")

async def llm_stream(prompt: str):
    """模拟 LLM 流式生成"""
    for i in range(10):
        await asyncio.sleep(0.1)
        yield f"Token-{i} "
```

**适用场景**:
- 实时聊天
- LLM 流式输出
- 实时通知

**设计提示**:
- 对接只提供 SSE 的大模型服务时，可在服务端用 WebSocket 封装成双向通道，方便前端多轮交互
- 保持连接计数与心跳监控，防止连接泄漏或异常断开后资源未释放
- 明确消息协议（事件类型/负载/错误码），避免前后端对齐成本；在异常/超时后主动关闭连接并清理会话

---

## 5.3 数据库连接池

### asyncpg 连接池

**目录**: `3/p28`

```python
import asyncpg
import asyncio

# 全局连接池
pool = None

async def init_db_pool():
    """初始化数据库连接池"""
    global pool
    pool = await asyncpg.create_pool(
        host='localhost',
        port=5432,
        user='postgres',
        password='password',
        database='mydb',
        min_size=10,  # 最小连接数
        max_size=50   # 最大连接数
    )

async def get_user(user_id: int):
    """使用连接池查询"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM users WHERE id = $1',
            user_id
        )
        return dict(row) if row else None

# 启动时初始化
@app.on_event("startup")
async def startup():
    await init_db_pool()

@app.on_event("shutdown")
async def shutdown():
    await pool.close()
```

**关键配置**:
- `min_size`: 预创建连接数 (减少延迟)
- `max_size`: 最大并发连接数
- 使用 `async with` 自动释放连接

### 选型与参数建议
- 驱动栈：高吞吐批量场景倾向 `asyncpg`；复杂建模/事务跨表逻辑可用 SQLAlchemy 2.0 async
- 池规模：`min_size`/`max_size` 结合并发和数据库核数设定，避免闲置连接过多；启用 keepalive 预防僵尸连接
- 超时策略：`connect_timeout`、`command_timeout`（驱动）与 `statement_timeout`（数据库端）协同控制端到端时延

---

## 5.4 速率限制与缓存

### Redis 缓存

**目录**: `3/p30`

```python
from aioredis import Redis
from fastapi import FastAPI, Request, HTTPException
import time

app = FastAPI()
redis = None

@app.on_event("startup")
async def startup():
    global redis
    redis = await Redis.from_url("redis://localhost")

# 速率限制装饰器
async def rate_limit(key: str, max_requests: int, window: int):
    """
    速率限制
    key: 限流键 (如 user_id)
    max_requests: 窗口内最大请求数
    window: 时间窗口 (秒)
    """
    current = await redis.incr(key)

    if current == 1:
        await redis.expire(key, window)

    if current > max_requests:
        raise HTTPException(status_code=429, detail="Too Many Requests")

@app.get("/api/data")
async def get_data(request: Request):
    # 速率限制: 每分钟 60 次
    await rate_limit(f"rate:{request.client.host}", 60, 60)

    # 缓存查询
    cache_key = "data:latest"
    cached = await redis.get(cache_key)

    if cached:
        return {"data": cached.decode(), "from_cache": True}

    # 查询数据库
    data = await query_database()

    # 缓存 10 分钟
    await redis.setex(cache_key, 600, data)

    return {"data": data, "from_cache": False}
```

**设计提示**:
- 令牌桶/漏桶限流：对每个客户端（IP/用户/租户）维护独立桶，超限返回 429 并带上 `Retry-After`
- 缓存风险：缓存穿透（无效 key 反复查询）、缓存击穿（热点 key 失效瞬间并发穿透）、缓存雪崩（大量 key 同时过期）；可用布隆过滤器、互斥填充和随机过期时间缓解

**工程经验速记**:
- 限流策略尽量靠近入口（网关/中间件），并区分用户/租户/接口维度；监控限流命中率辅助容量规划
- 缓存更新选择写穿/写回策略要结合一致性需求；热点 key 加互斥锁或单飞填充，避免击穿
- 对缓存依赖路径设置降级策略（如返回兜底数据或略降精度），保证缓存失效时服务可用

---

# 第六部分：LangChain/LangGraph 异步工作流

## 6.1 LangChain 异步 API

### ainvoke() vs invoke()

LangChain 在 LCEL 的 `Runnable` 接口上提供异步方法 (`ainvoke`/`abatch`/`astream`)；链中每个节点只要是 `async def` 就能被事件循环调度，实现端到端的异步流水线。

**文件**: `4/p32langchain调用/异步API.py`

```python
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio

# 构建链
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "What is a good name for a company that makes {product}?"),
])
llm = ChatTongyi(model="qwen-turbo", temperature=0.9)
chain = prompt | llm | StrOutputParser()

# 同步调用 (串行)
def generate_serially():
    for _ in range(5):
        result = chain.invoke({"product": "toothpaste"})

# 异步调用 (并发)
async def generate_concurrently():
    tasks = [
        chain.ainvoke({"product": "toothpaste"})
        for _ in range(5)
    ]
    results = await asyncio.gather(*tasks)
    return results

# 性能对比
import time

start = time.time()
asyncio.run(generate_concurrently())
print(f"并发: {time.time() - start:.2f}s")  # ~2s

start = time.time()
generate_serially()
print(f"串行: {time.time() - start:.2f}s")  # ~10s
```

**加速比**: ~5x (5 个并发请求)

**工程经验速记**:
- 统一用异步接口（`ainvoke`/`astream`），避免链中混入阻塞调用；遇到不支持异步的组件，外层包线程池
- 控制并发：对上游 API 设置信号量/令牌桶，防止 LLM/检索接口被打爆
- 流式接口 (`astream`) 需要及时消费，下游如果慢需做队列缓冲或背压

---

## 6.2 LangGraph 异步节点

### StateGraph 异步工作流

**文件**: `4/p34常见异步陷阱及规避/LangGraph图的异步调用.py`

```python
from langgraph.graph import StateGraph, START, END
import asyncio

# 模拟异步工具
async def weather(city: str) -> str:
    await asyncio.sleep(0.5)  # 模拟 API 调用
    return f"{city} 晴，25°C"

# 异步节点
async def get_weather(state):
    city = state.get("city", "北京")
    result = await weather(city)
    return {"result": result}

# 构建工作流
workflow = StateGraph(dict)
workflow.add_node("get_weather", get_weather)
workflow.add_edge(START, "get_weather")
workflow.add_edge("get_weather", END)

# 运行
async def main():
    app = workflow.compile()
    inputs = {"city": "上海"}

    # 流式输出
    async for event in app.astream(inputs):
        print(event)

asyncio.run(main())
# 输出: {'get_weather': {'result': '上海 晴，25°C'}}
```

**关键点**:
- 节点函数必须是 `async def`
- 使用 `astream()` 流式返回中间结果
- 支持复杂的条件路由

**工程经验速记**:
- 状态字典保持小而明确，避免在节点间传递大对象；需要大数据时用引用/缓存
- 对每个节点设置超时/重试策略，避免单节点拖住整张图
- 复杂路由中用可观测性（日志/事件流）追踪执行路径，便于排障

---

## 6.3 重试与超时机制

### LangGraph 重试机制

**文件**: `4/p34常见异步陷阱及规避/LangGraph图的的重试机制.py`

```python
from langgraph.graph import StateGraph
import asyncio

async def unstable_llm_call(state):
    """模拟不稳定的 LLM 调用"""
    import random

    if random.random() < 0.5:
        raise Exception("API 超时")

    return {"result": "Success"}

# 重试包装器
async def retry_node(state, max_retries=3):
    """带重试的节点"""
    for attempt in range(max_retries):
        try:
            return await unstable_llm_call(state)
        except Exception as e:
            if attempt == max_retries - 1:
                return {"error": str(e), "retries": attempt + 1}
            print(f"重试 {attempt + 1}/{max_retries}")
            await asyncio.sleep(2 ** attempt)  # 指数退避

# 超时控制
async def timeout_node(state):
    """带超时的节点"""
    try:
        result = await asyncio.wait_for(
            unstable_llm_call(state),
            timeout=5.0  # 5 秒超时
        )
        return result
    except asyncio.TimeoutError:
        return {"error": "超时"}
```

**最佳实践**:
- 使用指数退避避免请求风暴
- 设置合理的超时时间 (根据 API SLA)
- 记录重试次数用于监控
- 可在节点外层包装装饰器，统一用 `asyncio.wait_for`/重试策略读取集中配置 (如 `NODE_TIMEOUTS`)
- 使用 `pytest-asyncio` 为关键异步节点编写回归测试，覆盖超时/重试分支

---

## 6.4 自定义回调处理器

LangChain 会在执行 `Runnable`/链时收集 `config.callbacks`，构建内部回调管理器；链启动触发 `on_chain_start`，随后在 token 流式产出、链结束或异常时依次回调。借助自定义异步处理器可以做进度上报、流式打印、指标采集等。

### 异步回调跟踪

**文件**: `4/p33自定义回调处理器/回调过程跟踪_qwen.py`

```python
from langchain.callbacks.base import AsyncCallbackHandler
from langchain_community.chat_models.tongyi import ChatTongyi

class CustomAsyncCallback(AsyncCallbackHandler):
    """自定义异步回调"""

    async def on_llm_start(self, serialized, prompts, **kwargs):
        """LLM 开始调用"""
        print(f"[START] 发送提示词: {prompts[0][:50]}...")

    async def on_llm_new_token(self, token: str, **kwargs):
        """流式 token 到达"""
        print(token, end='', flush=True)

    async def on_llm_end(self, response, **kwargs):
        """LLM 调用结束"""
        print(f"\n[END] 总 tokens: {response.llm_output['token_usage']}")

    async def on_llm_error(self, error: Exception, **kwargs):
        """LLM 调用错误"""
        print(f"[ERROR] {error}")

# 使用回调
async def main():
    llm = ChatTongyi(
        model="qwen-turbo",
        streaming=True,
        callbacks=[CustomAsyncCallback()]
    )

    async for chunk in llm.astream("你好"):
        pass  # 回调自动处理

asyncio.run(main())
```

**工程经验速记**:
- 回调里避免重逻辑；只做轻量记录/上报，把耗时工作排队到后台任务
- 进度上报可统一通过 WebSocket/事件队列传给前端或监控系统，避免在业务链路里做阻塞 I/O
- 为回调增加超时/异常保护，保证不会影响主链路执行

---

# 第七部分：GPU 加速与向量检索

## 7.1 FAISS GPU 索引

### GPU 向量索引构建

**文件**: `5/p36CUDA与异步GPU.py`

```python
import numpy as np
import faiss
import asyncio
from concurrent.futures import ThreadPoolExecutor

POOL = ThreadPoolExecutor()

def build_gpu_index(embeddings: np.ndarray):
    """构建 GPU 向量索引"""
    d = embeddings.shape[1]  # 向量维度
    embeddings = np.ascontiguousarray(embeddings.astype('float32'))

    # 创建 CPU 索引
    index_cpu = faiss.IndexFlatIP(d)  # Inner Product (余弦相似度)

    # 尝试转移到 GPU
    try:
        ngpus = faiss.get_num_gpus()
        if ngpus >= 1:
            res = faiss.StandardGpuResources()
            res.setTempMemory(512 * 1024 * 1024)  # 512MB 临时内存

            if ngpus == 1:
                index_gpu = faiss.index_cpu_to_gpu(res, 0, index_cpu)
            else:
                index_gpu = faiss.index_cpu_to_all_gpus(index_cpu)

            index_gpu.add(embeddings)
            print(f"使用 GPU 索引，GPU 数={ngpus}")
            return index_gpu
    except Exception as e:
        print(f"GPU 不可用，回退到 CPU: {e}")

    # 回退到 CPU
    index_cpu.add(embeddings)
    print("使用 CPU 索引")
    return index_cpu
```

**关键配置**:
- `IndexFlatIP`: 内积索引 (适合余弦相似度)
- `setTempMemory()`: 设置 GPU 临时内存大小
- 自动回退到 CPU (兼容性)

**工程经验速记**:
- 先确认 GPU/驱动/Faiss 版本兼容；多 GPU 时优先用 `index_cpu_to_all_gpus` 均衡负载
- 构建前把向量转为 `float32` 并保证连续内存；大批量 add 时分批送入，避免显存峰值
- 预留回退路径（CPU 索引）和健康检查，避免线上因 GPU 不可用导致不可用

---

## 7.2 异步向量搜索

### 非阻塞向量检索

**文件**: `5/p36CUDA与异步GPU.py`

```python
async def async_search(index, query_vec: np.ndarray, k=3):
    """
    异步执行向量搜索
    使用 ThreadPoolExecutor 避免阻塞事件循环
    """
    loop = asyncio.get_running_loop()
    q = np.ascontiguousarray(query_vec.astype('float32'))

    # 在线程池中执行 FAISS 搜索
    similarities, indices = await loop.run_in_executor(
        POOL,
        lambda: index.search(q, k)
    )

    return similarities, indices

async def main():
    # 构建索引
    np.random.seed(42)
    embeddings = np.random.rand(10_000, 128).astype('float32')
    embeddings = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)

    index = build_gpu_index(embeddings)

    # 并发搜索 (模拟多 Agent 检索)
    queries = np.random.rand(5, 128).astype('float32')
    queries = queries / (np.linalg.norm(queries, axis=1, keepdims=True) + 1e-8)

    tasks = [async_search(index, q.reshape(1, -1)) for q in queries]
    results = await asyncio.gather(*tasks)

    for i, (sim, idx) in enumerate(results):
        print(f"查询 {i}: 相似度={sim[0,0]:.3f}, 最近邻 ID={idx[0,0]}")

asyncio.run(main())
```

**性能优化**:
- GPU 索引构建加速 ~10x
- 异步搜索支持高并发
- 适用于多 Agent RAG 场景

**工程经验速记**:
- 检索调用用线程池/进程池包裹，避免阻塞事件循环；并发数与 GPU 能力匹配
- 对批量查询优先使用批量 search，吞吐通常高于单条并发
- 记录查询耗时与显存占用，提前设定告警阈值

---

# 第八部分：性能分析与优化

## 8.1 性能基准测试

### 吞吐量与延迟测试

**文件**: `p18_1IO密集场景综合性能测试.py`

```python
import time
import asyncio
from dataclasses import dataclass
from typing import List

@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_requests: int
    total_time: float
    throughput: float  # 请求/秒
    mean_latency: float  # 平均延迟 (ms)
    p95_latency: float  # 95分位延迟 (ms)
    p99_latency: float  # 99分位延迟 (ms)
    success_rate: float  # 成功率

async def benchmark_async(num_requests=100):
    """异步性能基准测试"""
    latencies = []
    errors = 0

    async def single_request():
        start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://httpbin.org/get") as resp:
                    await resp.text()
            latencies.append((time.time() - start) * 1000)
        except Exception:
            errors += 1

    start_time = time.time()
    tasks = [single_request() for _ in range(num_requests)]
    await asyncio.gather(*tasks)
    total_time = time.time() - start_time

    latencies.sort()

    return PerformanceMetrics(
        total_requests=num_requests,
        total_time=total_time,
        throughput=num_requests / total_time,
        mean_latency=sum(latencies) / len(latencies),
        p95_latency=latencies[int(len(latencies) * 0.95)],
        p99_latency=latencies[int(len(latencies) * 0.99)],
        success_rate=(num_requests - errors) / num_requests
    )

# 运行测试
metrics = asyncio.run(benchmark_async(100))
print(f"吞吐量: {metrics.throughput:.2f} req/s")
print(f"平均延迟: {metrics.mean_latency:.2f} ms")
print(f"P95 延迟: {metrics.p95_latency:.2f} ms")
print(f"成功率: {metrics.success_rate*100:.1f}%")
```

**示例基准 (I/O 密集)**:
- 同步模型：吞吐 ~120 req/s，P99 ~850ms
- `asyncio`：吞吐可达 ~3200 req/s，P99 ~120ms
- 关注 P95/P99 等长尾指标，而不仅是平均延迟

---

## 8.2 Profiling 工具

### cProfile 与 py-spy

```python
# 1. cProfile (函数级性能分析)
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # 运行代码
    asyncio.run(your_async_function())

    profiler.disable()

    # 输出统计
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 函数

# 2. py-spy (实时采样分析器)
# 命令行运行:
# py-spy top --pid <PID>  # 实时查看
# py-spy record -o profile.svg -- python your_script.py  # 生成火焰图
```

**诊断原则**:
- 先判断瓶颈是 I/O 等待、CPU 计算还是锁竞争，避免盲目优化
- 80/20 法则：大多数性能问题集中在少数热点路径，优先聚焦
- 开发期用 `cProfile` 精确到函数级；生产用 `py-spy` 采样，做到零侵入、无需重启服务

**工程经验速记**:
- 采样频率与开销平衡：生产用低频采样获取趋势，局部问题再提高频率/缩小范围
- 结合指标/日志/trace 定位：CPU 高但 I/O 低可能是锁竞争或忙等，网络指标异常则看重试/超时
- 火焰图前先去除噪声（探活/metrics），让热点更清晰

---

## 8.3 最佳实践总结

### 1. 选择正确的并发模型

```python
# 决策树
if task_is_io_bound():
    if need_simplicity():
        use_asyncio()  # ✅ 推荐
    elif have_legacy_sync_code():
        use_multithreading()
elif task_is_cpu_bound():
    if task_can_be_parallelized():
        use_multiprocessing()  # ✅ 推荐
    else:
        optimize_algorithm()  # 单线程优化
```

### 2. 避免常见陷阱

**陷阱 1: 在协程中调用阻塞函数**
```python
# ❌ 错误
async def bad_example():
    result = requests.get("https://...")  # 阻塞整个事件循环
    return result

# ✅ 正确
async def good_example():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://...") as resp:
            return await resp.text()
```

**陷阱 2: 忘记 await**
```python
# ❌ 错误
async def bad_example():
    task = asyncio.create_task(some_coro())
    # 忘记 await, 任务可能未完成就退出

# ✅ 正确
async def good_example():
    task = asyncio.create_task(some_coro())
    result = await task  # 等待完成
```

**陷阱 3: 过度并发**
```python
# ❌ 错误 (可能耗尽连接/内存)
tasks = [fetch_url(url) for url in urls]  # 10000+ 并发
await asyncio.gather(*tasks)

# ✅ 正确 (限制并发数)
semaphore = asyncio.Semaphore(50)

async def bounded_fetch(url):
    async with semaphore:
        return await fetch_url(url)

tasks = [bounded_fetch(url) for url in urls]
await asyncio.gather(*tasks)
```

### 3. 连接池最佳实践

```python
# ✅ HTTP 连接池
connector = aiohttp.TCPConnector(
    limit=100,          # 总连接数
    limit_per_host=10,  # 每个主机连接数
    ttl_dns_cache=300   # DNS 缓存时间
)
session = aiohttp.ClientSession(connector=connector)

# ✅ 数据库连接池
pool = await asyncpg.create_pool(
    host='localhost',
    min_size=10,
    max_size=50,
    command_timeout=60
)
```

### 4. 优雅关闭

```python
import signal
import asyncio

shutdown_event = asyncio.Event()

def signal_handler(sig, frame):
    print("收到退出信号，开始优雅关闭...")
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def main():
    # 启动后台任务
    tasks = [
        asyncio.create_task(worker_1()),
        asyncio.create_task(worker_2())
    ]

    # 等待关闭信号
    await shutdown_event.wait()

    # 取消所有任务
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    # 关闭资源
    await db_pool.close()
    await redis.close()

    print("优雅关闭完成")

asyncio.run(main())
```

---

## 总结

### Python 异步并发 核心要点

| 主题 | 关键技术 | 适用场景 |
|------|---------|---------|
| **异步 I/O** | `asyncio`, `aiohttp`, `asyncpg` | Web API, 爬虫, 数据库操作 |
| **并发模式** | 协程, 多线程, 多进程 | 根据任务类型选择 |
| **任务调度** | `Future`, `Task`, `Executor` | 混合 CPU/IO 任务 |
| **LangChain** | `ainvoke()`, `astream()` | LLM 应用并发 |
| **LangGraph** | 异步节点, 重试机制 | 复杂 AI 工作流 |
| **GPU 加速** | FAISS GPU, 异步检索 | 向量数据库, RAG |
| **监控优化** | Profiling, 基准测试 | 性能调优 |

### 推荐学习路径

1. **基础** (1-2 天)
   - 掌握 `async/await` 语法
   - 理解事件循环机制
   - 学会使用 `asyncio.gather()`

2. **进阶** (3-5 天)
   - 学习 `aiohttp` / `httpx`
   - 掌握数据库连接池
   - 理解 GIL 影响

3. **高级** (1 周)
   - 设计混合并发架构
   - LangChain/LangGraph 异步工作流
   - GPU 加速集成

4. **生产实践** (持续)
   - 性能监控与优化
   - 错误处理与重试
   - 优雅关闭与资源清理

---

**文档版本**: v1.0
**最后更新**: 2025-12-15
**课程来源**: AI 工程师训练营 Python 异步并发
**作者**: Claude (Anthropic)
