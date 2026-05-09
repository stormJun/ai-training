"""Additional LangChain experiment using the same Qwen-compatible setup."""

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("04_langchain_qwen_basic.py")


def load_main_module():
    spec = importlib.util.spec_from_file_location("langchain_05", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    module = load_main_module()
    print(module.run_basic_chat("请用两句话说明 LangChain 的作用。"))
