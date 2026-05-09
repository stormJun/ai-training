import importlib.util
import os
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = PROJECT_DIR / "04_langchain_qwen_basic.py"


def load_module(module_name: str):
    sys.modules.pop("langchain_openai", None)
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_key_returns_clear_message(tmp_path, monkeypatch):
    fake_pkg = tmp_path / "langchain_openai"
    fake_pkg.mkdir()
    (fake_pkg / "__init__.py").write_text(
        """
class ChatOpenAI:
    def __init__(self, *args, **kwargs):
        pass
""",
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_BASE", "")

    module = load_module("langchain_05_missing")

    result = module.run_basic_chat("你好")

    assert "DASHSCOPE_API_KEY" in result


def test_qwen_defaults_are_used(tmp_path, monkeypatch):
    fake_pkg = tmp_path / "langchain_openai"
    fake_pkg.mkdir()
    (fake_pkg / "__init__.py").write_text(
        """
class _Response:
    def __init__(self, content):
        self.content = content


class ChatOpenAI:
    def __init__(self, base_url=None, api_key=None, model=None, temperature=None):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def invoke(self, prompt):
        return _Response(f"{self.model}|{self.base_url}|{self.api_key}|{prompt}")
""",
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-qwen-test")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_BASE", "")

    module = load_module("langchain_05_qwen")

    result = module.run_basic_chat("你好")

    assert (
        result
        == "qwen-plus|https://dashscope.aliyuncs.com/compatible-mode/v1|sk-qwen-test|你好"
    )
