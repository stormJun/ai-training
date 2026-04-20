"""Tool-calling example using Qwen-compatible OpenAI API."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


ENV_FILE = Path(__file__).with_name(".env")
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"


def build_client() -> OpenAI:
    load_dotenv(dotenv_path=ENV_FILE)

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE") or DEFAULT_BASE_URL

    if not api_key:
        print("Missing DASHSCOPE_API_KEY.")
        print("Please set your Qwen/DashScope API key before running this script.")
        print("Example:")
        print("  export DASHSCOPE_API_KEY=your_api_key_here")
        print(f"  export OPENAI_API_BASE={DEFAULT_BASE_URL}")
        raise SystemExit(1)

    try:
        return OpenAI(base_url=base_url, api_key=api_key)
    except Exception as exc:
        print("Failed to initialize OpenAI-compatible client.")
        print(f"Details: {exc}")
        print("Please check your installed openai/httpx versions.")
        raise SystemExit(1)


def get_horoscope(sign: str) -> str:
    return f"{sign}: 下周二你将结识一只小水獭。"


def main() -> int:
    client = build_client()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_horoscope",
                "description": "获取指定星座的今日运势",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sign": {
                            "type": "string",
                            "description": "星座名称，如金牛座或水瓶座",
                        },
                    },
                    "required": ["sign"],
                },
            },
        }
    ]

    messages = [{"role": "user", "content": "我的运势如何？我是水瓶座。"}]

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        tools=tools,
        messages=messages,
    )

    print("模型初始输出:")
    print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))

    assistant_message = response.choices[0].message
    messages.append(assistant_message)

    if not assistant_message.tool_calls:
        print("模型没有发起工具调用。")
        return 0

    tool_call = assistant_message.tool_calls[0]
    function_call_arguments = json.loads(tool_call.function.arguments)

    result = {"horoscope": get_horoscope(function_call_arguments["sign"])}
    messages.append(
        {
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": "get_horoscope",
            "content": json.dumps(result, ensure_ascii=False),
        }
    )

    print("消息流程:")
    for index, message in enumerate(messages, start=1):
        if isinstance(message, dict):
            if message["role"] == "user":
                print(f"{index}. 用户输入: {message['content']}")
            elif message["role"] == "tool":
                print(f"{index}. 工具返回: {json.loads(message['content'])}")
        else:
            print(f"{index}. 助手: 调用工具 {message.tool_calls[0].function.name}")

    final_response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        tools=tools,
        messages=messages,
    )

    print("最终输出:")
    print(json.dumps(final_response.model_dump(), indent=2, ensure_ascii=False))
    print(f"\n{final_response.choices[0].message.content}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
