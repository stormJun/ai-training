"""Minimal Qwen-compatible API call example."""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"


def mask_secret(secret: str) -> str:
    if len(secret) <= 10:
        return f"{secret[:2]}******"
    return f"{secret[:10]}******"


def build_client() -> OpenAI:
    load_dotenv()

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE") or DEFAULT_BASE_URL

    if not api_key:
        print("Missing DASHSCOPE_API_KEY.")
        print("Please set your Qwen/DashScope API key before running this script.")
        print("Example:")
        print("  export DASHSCOPE_API_KEY=your_api_key_here")
        print(f"  export OPENAI_API_BASE={DEFAULT_BASE_URL}")
        raise SystemExit(1)

    print(f"-- debug -- dashscope api key is {mask_secret(api_key)}")
    print(f"-- debug -- base url is {base_url}")

    return OpenAI(base_url=base_url, api_key=api_key)


def main() -> int:
    client = build_client()

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": "Hello world!"}],
    )

    print(response.choices[0].message.content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
