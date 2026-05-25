# Python 并发与性能

本目录汇总仓库中的 Python 并发、异步、性能与调度相关主题，尽量保留原有子目录结构，方便按“基础机制 -> Web 模式 -> 性能分析 -> 混合调度”的顺序学习。

## 子目录

- `01_asyncio_and_gil_basics/`
  - asyncio 基础、协程语法、Future、Task、Executor、GIL
- `02_async_web_patterns/`
  - 异步 Web、I/O 模式与常见工程模式
- `03_performance_benchmarking/`
  - 压测、profiling 与性能分析
- `04_async_multiprocess_hybrid/`
  - 协程与多进程混合调度

## 建议顺序

1. `01_asyncio_and_gil_basics/`
2. `02_async_web_patterns/`
3. `03_performance_benchmarking/`
4. `04_async_multiprocess_hybrid/`
