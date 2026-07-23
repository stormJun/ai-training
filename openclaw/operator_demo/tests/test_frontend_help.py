from pathlib import Path


def test_frontend_has_help_button_and_usage_dialog():
    html = Path("openclaw/operator_demo/static/index.html").read_text(encoding="utf-8")

    assert 'id="helpButton"' in html
    assert 'id="helpDialog"' in html
    assert "操作步骤" in html
    assert "运行默认工作流" in html
    assert "单算子执行" in html
