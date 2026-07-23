"""Basic chat example using Qwen-compatible OpenAI API."""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


ENV_FILE = Path(__file__).with_name(".env")
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"


def get_client() -> OpenAI | None:
    load_dotenv(dotenv_path=ENV_FILE)

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE") or DEFAULT_BASE_URL

    if not api_key:
        return None

    try:
        return OpenAI(base_url=base_url, api_key=api_key)
    except Exception:
        return None


def query(user_prompt: str) -> str:
    """Send a prompt to the Qwen-compatible chat API and return the response."""
    client = get_client()
    if client is None:
        return (
            "Missing DASHSCOPE_API_KEY. "
            "Please configure your Qwen/DashScope API key in 01_langchain_basics/.env "
            "or check your openai/httpx dependency versions."
        )

    try:
        # OpenAI官方Python SDK 调用对话大模型的标准请求代码，作用：向大模型发送提问，接收模型返回的全部数据，存入变量 response
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": user_prompt}],
        )
        # {
        #     "id": "chatcmpl-xxx",
        #     "object": "chat.completion",
        #     "created": 1700000000,
        #     "model": "gpt-3.5-turbo",
        #     "choices": [
        #         {
        #             "index": 0,
        #             "message": {
        #                 "role": "assistant",
        #                 "content": "你好，我是AI助手"
        #             },
        #             "finish_reason": "stop"
        #         }
        #     ],
        #     "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        # }
        return response.choices[0].message.content
    except Exception as exc:
        return f"错误: {exc}"


if __name__ == "__main__":
    print(query("早上好，今天想聊点什么呢?"))
