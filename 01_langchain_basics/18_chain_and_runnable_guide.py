"""Runnable and chain examples extracted from the original notebook."""

import asyncio
import time
from typing import Iterator

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnableBranch, RunnableLambda, RunnableParallel


# 这一部分对应 notebook 中对 LCEL 的解释：
# LangChain 通过 __or__ / __ror__ 支持 prompt | model | parser 这样的写法。


def demo_prompt_schema() -> None:
    """查看 PromptTemplate 的输入输出 schema。"""
    prompt = PromptTemplate(
        input_variables=["name", "age"],
        template="你好，我是{name}，今年{age}岁",
    )
    print(prompt.input_schema.schema())
    print(prompt.output_schema.schema())


class SimpleRunnable:
    """演示 invoke / ainvoke 的基本关系。"""

    def invoke(self, user_input: str) -> str:
        time.sleep(0.2)
        return f"结果: {user_input}"

    async def ainvoke(self, user_input: str) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.invoke, user_input)


class SimpleStreamRunnable(Runnable[str, str]):
    """演示 stream 的逐步返回。"""

    def invoke(self, user_input: str) -> str:
        return f"完整处理结果: {user_input}"

    def stream(self, user_input: str) -> Iterator[str]:
        words = f"逐步处理结果: {user_input}".split()
        for word in words:
            time.sleep(0.1)
            yield word + " "


class SimpleAnalyzer(Runnable[str, str]):
    """演示 batch 的最小自定义 Runnable。"""

    def invoke(self, user_input: str, config=None) -> str:
        return f"分析结果: {user_input} -> 类型:文档, 重要性:中等"


def build_parallel_demo():
    """演示并行组合。"""
    return RunnableParallel(
        summary=RunnableLambda(lambda x: f"摘要: {x['text']}"),
        keywords=RunnableLambda(lambda x: ["LangChain", "Runnable", "Parser"]),
        sentiment=RunnableLambda(lambda x: "positive"),
    )


def build_branch_demo():
    """演示条件分支。"""
    qa_chain = RunnableLambda(lambda x: f"问答处理: {x['content']}")
    summary_chain = RunnableLambda(lambda x: f"摘要处理: {x['content']}")
    default_chain = RunnableLambda(lambda x: f"通用处理: {x['content']}")

    return RunnableBranch(
        (lambda x: x["type"] == "question", qa_chain),
        (lambda x: x["type"] == "summary", summary_chain),
        default_chain,
    )


async def demo_async() -> None:
    runnable = SimpleRunnable()
    print(await runnable.ainvoke("异步输入"))


def demo_stream() -> None:
    runnable = SimpleStreamRunnable()
    for chunk in runnable.stream("流式输出"):
        print(chunk, end="", flush=True)
    print()


def demo_batch() -> None:
    analyzer = SimpleAnalyzer()
    results = analyzer.batch(["报告A", "合同B", "邮件C"])
    print(results)


def demo_parallel() -> None:
    parallel = build_parallel_demo()
    print(parallel.invoke({"text": "分析这段文本"}))


def demo_branch() -> None:
    branch = build_branch_demo()
    print(branch.invoke({"type": "question", "content": "什么是 LCEL？"}))
    print(branch.invoke({"type": "summary", "content": "总结这段文本"}))
    print(branch.invoke({"type": "other", "content": "做一个通用分析"}))


if __name__ == "__main__":
    demo_prompt_schema()
    asyncio.run(demo_async())
    demo_stream()
    demo_batch()
    demo_parallel()
    demo_branch()
