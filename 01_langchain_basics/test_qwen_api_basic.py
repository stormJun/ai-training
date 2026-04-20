import os
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent / "qwen_api_basic.py"


def test_script_reports_missing_dashscope_api_key():
    env = os.environ.copy()
    env["DASHSCOPE_API_KEY"] = ""
    env["OPENAI_API_KEY"] = ""
    env["OPENAI_API_BASE"] = ""

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        env=env,
        cwd=SCRIPT_PATH.parent,
    )

    assert result.returncode == 1
    assert "DASHSCOPE_API_KEY" in result.stdout
    assert "Traceback" not in result.stderr


def test_script_uses_qwen_defaults_and_prints_response(tmp_path):
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
        return _Response(f"{model}|{self.outer.base_url}|{self.outer.api_key}")


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

    env = os.environ.copy()
    env["DASHSCOPE_API_KEY"] = "sk-test-qwen-key"
    env.pop("OPENAI_API_KEY", None)
    env.pop("OPENAI_API_BASE", None)
    env["PYTHONPATH"] = f"{tmp_path}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        env=env,
        cwd=SCRIPT_PATH.parent,
    )

    assert result.returncode == 0
    assert "qwen-plus|https://dashscope.aliyuncs.com/compatible-mode/v1|sk-test-qwen-key" in result.stdout
