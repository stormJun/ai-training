<!-- Converted from 01_asyncio_overview.ipynb -->

```python
import time

def task(name, seconds):
    print(f"任务 {name} 开始")
    time.sleep(seconds)
    print(f"任务 {name} 完成")

def sync_example():
    start_time = time.time()
    task("下载文件", 2)
    task("处理数据", 2)
    task("保存结果", 2)
    end_time = time.time()
    print(f"耗时: {end_time - start_time:.2f} 秒")

if __name__ == "__main__":
    sync_example()

```

输出：

```text
任务 下载文件 开始
任务 下载文件 完成
任务 处理数据 开始
任务 处理数据 完成
任务 保存结果 开始
任务 保存结果 完成
耗时: 6.00 秒
```

```python
import asyncio
import time

import nest_asyncio
nest_asyncio.apply()

async def task(name, seconds):
    print(f"任务 {name} 开始")
    await asyncio.sleep(seconds)  # 使用异步的 sleep
    print(f"任务 {name} 完成")

async def async_example():
    start_time = time.time()
    # 并发执行任务：先显式创建，再统一等待
    t1 = asyncio.create_task(task("下载文件", 2))
    t2 = asyncio.create_task(task("处理数据", 1))
    t3 = asyncio.create_task(task("保存结果", 2))
    await asyncio.gather(t1, t2, t3)
    end_time = time.time()
    print(f"异步版本总耗时: {end_time - start_time:.2f} 秒")

if __name__ == "__main__":
    asyncio.run(async_example())
```

输出：

```text
任务 下载文件 开始
任务 处理数据 开始
任务 保存结果 开始
任务 处理数据 完成
任务 下载文件 完成
任务 保存结果 完成
异步版本总耗时: 20.01 秒
```
