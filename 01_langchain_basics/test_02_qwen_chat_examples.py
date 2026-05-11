import importlib.util
import os
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
CHAT_SCRIPT = PROJECT_DIR / "02_qwen_chat_basic.py"
TOOL_SCRIPT = PROJECT_DIR / "03_qwen_function_tool_calling_demo.py"


def load_module(module_name: str, file_path: Path):
    sys.modules.pop("openai", None)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_query_returns_missing_key_message_when_no_env(tmp_path, monkeypatch):
    fake_openai_dir = tmp_path / "openai"
    fake_openai_dir.mkdir()
    (fake_openai_dir / "__init__.py").write_text(
        """
class OpenAI:
    def __init__(self, *args, **kwargs):
        self.chat = type("Chat", (), {})()
""",
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_BASE", "")

    module = load_module("chat_04_missing", CHAT_SCRIPT)

    result = module.query("你好")

    assert "DASHSCOPE_API_KEY" in result


def test_query_uses_qwen_defaults(tmp_path, monkeypatch):
    fake_openai_dir = tmp_path / "openai"
    fake_openai_dir.mkdir()
    (fake_openai_dir / "__init__.py").write_text(
        """
class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, outer):
        self.outer = outer

    def create(self, model, messages):
        content = f"{model}|{self.outer.base_url}|{self.outer.api_key}|{messages[0]['content']}"
        return _Response(content)


class _Chat:
    def __init__(self, outer):
        self.completions = _Completions(outer)


class OpenAI:
    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.chat = _Chat(self)
""",
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-qwen-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)

    module = load_module("chat_04_qwen", CHAT_SCRIPT)

    result = module.query("你好")

    assert result == "qwen-plus|https://dashscope.aliyuncs.com/compatible-mode/v1|sk-qwen-test|你好"


def test_tool_call_script_reports_missing_key():
    env = os.environ.copy()
    env["DASHSCOPE_API_KEY"] = ""
    env["OPENAI_API_KEY"] = ""
    env["OPENAI_API_BASE"] = ""

    result = __import__("subprocess").run(
        [sys.executable, str(TOOL_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_DIR,
    )

    assert result.returncode == 1
    assert "DASHSCOPE_API_KEY" in result.stdout
