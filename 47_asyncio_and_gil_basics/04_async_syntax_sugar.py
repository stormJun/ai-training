"""async 语法糖演进示例。

这个文件由 p6_async语法糖.ipynb 转换而来。
处理原则：

1. 保留原 notebook 的讲解顺序
2. 把 markdown 说明改写成中文注释
3. 把原本的代码单元尽量原样保留
4. 对已经过时、在 Python 3.12 里不能直接运行的旧语法，明确标注为“讲解代码”
"""

from __future__ import annotations

import asyncio
import dis


# ============================================================
# 阶段 1：基于生成器的协程（Python 2.5+）
# ============================================================
#
# 在 async / await 语法出现之前，Python 最早是借助“生成器”来模拟协程的。
# 这里最关键的理解是：
#
# - `yield` 不只是“生成一个值”
# - 它还可以把函数执行暂停在当前位置
# - 下次恢复执行时，可以继续从中断点往下走
#
# 这种“可暂停、可恢复”的特性，正是协程模型最早的基础。

def simple_generator():
    """最小生成器示例。

    这个例子不是 asyncio 协程本身，而是帮助理解：
    为什么“生成器”可以成为后续协程语法的基础。
    """

    yield 1
    x = yield 2
    yield x + 3


def demo_simple_generator() -> None:
    """演示 next()/send() 如何驱动生成器暂停与恢复。"""

    gen = simple_generator()
    print(next(gen))       # 先运行到 yield 1，返回 1
    print(gen.send(10))    # 恢复执行，把 10 送进 x，但当前返回的仍然是 yield 2
    print(gen.send(10))    # 再次恢复，这时 x=10，所以返回 13

    try:
        print(next(gen))   # 生成器已经结束，会抛 StopIteration
    except StopIteration:
        print("StopIteration")


# ============================================================
# 阶段 2：@asyncio.coroutine 装饰器（Python 3.4）
# ============================================================
#
# 在 Python 3.4 时代，官方开始把“基于生成器的协程”做成更明确的异步写法。
# 那时候还没有 async / await，而是：
#
# - 用 `@asyncio.coroutine` 标记“这是协程”
# - 用 `yield from` 等待另一个协程/生成器
#
# 但要注意：
#
# 这套写法在 Python 3.12 中已经被移除。
# 所以下面这段代码保留的目的主要是“讲解历史语法”，不是为了直接执行。


# 协程雏形（Python 3.4）
# 在 Python 3.12 中，@asyncio.coroutine 已被移除。
#
# 下面这段写法只作为“历史语法讲解代码”保留：
#
# @asyncio.coroutine
# def old_style_coro():
#     print("Start")
#     yield from asyncio.sleep(1)
#     print("End")
#
# 现代写法会改成：
#
# async def native_coro():
#     print("Start")
#     await asyncio.sleep(1)
#     print("End")


def old_style_coro_expanded():
    """手工展开 yield from 的核心思路。

    这不是推荐写法，也不是生产代码，只是为了说明：
    `yield from` 本质上是在“把当前生成器的控制权委托给另一个生成器”。
    """

    print("Start")

    # 这里用 asyncio.sleep(1) 只是为了借一个“可等待对象”做讲解。
    # 在真实旧式协程里，yield from 的核心思想就是：
    # “把当前函数的暂停/恢复逻辑交给另一个生成器继续处理”。
    sleep_gen = asyncio.sleep(1).__await__()

    try:
        while True:
            value = next(sleep_gen)
            try:
                yielded_value = yield value
            except Exception as e:  # noqa: PERF203 - 这里只是展开语义
                sleep_gen.throw(e)
            else:
                sleep_gen.send(yielded_value)
    except StopIteration:
        pass

    print("End")


# ============================================================
# 阶段 3：原生协程（Python 3.5+）
# ============================================================
#
# Python 3.5 之后，官方提供了 async / await 语法。
# 这是现在最常用、最推荐的协程写法。
#
# 你可以把它理解成：
#
# - `async def` 是“协程函数”的正式语法
# - `await` 是“等待另一个异步操作，同时让出执行权”的正式语法
# - 它本质上是对旧式 `yield from` 协程的一层语法糖


async def native_coro():
    """原生协程示例。"""

    print("Start")
    await asyncio.sleep(1)  # 语法糖层面替代旧式 yield from
    print("End")


def demo_dis_native_coro() -> None:
    """反汇编查看原生协程的字节码。"""

    dis.dis(native_coro)


if __name__ == "__main__":
    print("=== 阶段 1：生成器协程基础 ===")
    demo_simple_generator()

    print("\n=== 阶段 2：旧式协程的 yield from 展开思路 ===")
    print("这部分只保留讲解代码，不直接运行 @asyncio.coroutine 旧语法。")
    print("old_style_coro_expanded 定义已保留，可配合源码阅读理解 yield from 的委托机制。")

    print("\n=== 阶段 3：原生协程字节码 ===")
    demo_dis_native_coro()
