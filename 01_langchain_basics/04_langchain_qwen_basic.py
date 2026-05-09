"""Minimal LangChain example using Qwen-compatible OpenAI API."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


ENV_FILE = Path(__file__).with_name(".env")
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"


def get_llm() -> ChatOpenAI | None:
    load_dotenv(dotenv_path=ENV_FILE)

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE") or DEFAULT_BASE_URL

    if not api_key:
        return None

    try:
        return ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model=DEFAULT_MODEL,
            temperature=0.7,
        )
    except Exception:
        return None


def run_basic_chat(user_prompt: str) -> str:
    """Run a minimal LangChain chat example."""
    llm = get_llm()
    if llm is None:
        return (
            "Missing DASHSCOPE_API_KEY. "
            "Please configure your Qwen/DashScope API key in 01_langchain_basics/.env "
            "or check your langchain/openai dependency versions."
        )

    try:
        response = llm.invoke(user_prompt)
        return response.content
    except Exception as exc:
        return f"错误: {exc}"


if __name__ == "__main__":
    print(run_basic_chat("请用一句话介绍 LangChain。"))
