"""Behavior tests for the Harness Engineering CLI demo."""

from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "harness_demo.py"


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_can_stop_after_two_stages_and_leave_resume_state(tmp_path: Path) -> None:
    workspace = tmp_path / "run"

    result = run_cli("run", "--workspace", str(workspace), "--stop-after", "2", cwd=ROOT)

    assert result.returncode == 2
    assert "Simulated interruption after 2 stage(s)" in result.stderr

    progress = read_json(workspace / "progress.json")
    assert progress["completed_stages"] == ["read_plan", "draft_change"]
    assert progress["next_stage"] == "run_validation"
    assert progress["status"] == "interrupted"
    assert not (workspace / "verdict.json").exists()

    progress_log = (workspace / "progress.log").read_text(encoding="utf-8")
    assert "completed read_plan" in progress_log
    assert "completed draft_change" in progress_log


def test_run_resumes_from_progress_and_writes_passing_verdict(tmp_path: Path) -> None:
    workspace = tmp_path / "run"
    first = run_cli("run", "--workspace", str(workspace), "--stop-after", "2", cwd=ROOT)
    assert first.returncode == 2

    second = run_cli("run", "--workspace", str(workspace), cwd=ROOT)

    assert second.returncode == 0
    assert "Resuming from stage: run_validation" in second.stdout
    assert "Verdict: pass" in second.stdout

    progress = read_json(workspace / "progress.json")
    assert progress["completed_stages"] == [
        "read_plan",
        "draft_change",
        "run_validation",
        "write_verdict",
    ]
    assert progress["next_stage"] is None
    assert progress["status"] == "complete"

    verdict = read_json(workspace / "verdict.json")
    assert verdict["status"] == "pass"
    assert verdict["checks"] == [
        {"name": "progress_file_exists", "passed": True},
        {"name": "decision_log_exists", "passed": True},
        {"name": "validation_artifact_exists", "passed": True},
    ]
    assert verdict["resume_supported"] is True


def test_status_reports_next_stage_for_interrupted_run(tmp_path: Path) -> None:
    workspace = tmp_path / "run"
    first = run_cli("run", "--workspace", str(workspace), "--stop-after", "1", cwd=ROOT)
    assert first.returncode == 2

    status = run_cli("status", "--workspace", str(workspace), cwd=ROOT)

    assert status.returncode == 0
    assert "status: interrupted" in status.stdout
    assert "next_stage: draft_change" in status.stdout
