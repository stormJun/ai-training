from pathlib import Path
import subprocess
import sys


def test_langgraph_cli_is_installed() -> None:
    langgraph_cli = Path(sys.executable).with_name("langgraph")

    assert langgraph_cli.exists()

    result = subprocess.run(
        [str(langgraph_cli), "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
