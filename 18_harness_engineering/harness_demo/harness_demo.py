#!/usr/bin/env python3
"""A small Harness Engineering demo with resumable progress and verdicts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Callable


STAGES = ["read_plan", "draft_change", "run_validation", "write_verdict"]


@dataclass(frozen=True)
class RunState:
    status: str
    completed_stages: list[str]
    next_stage: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def progress_path(workspace: Path) -> Path:
    return workspace / "progress.json"


def load_state(workspace: Path) -> RunState:
    path = progress_path(workspace)
    if not path.exists():
        return RunState(status="new", completed_stages=[], next_stage=STAGES[0])

    raw = json.loads(path.read_text(encoding="utf-8"))
    return RunState(
        status=raw["status"],
        completed_stages=list(raw["completed_stages"]),
        next_stage=raw["next_stage"],
    )


def save_state(workspace: Path, state: RunState) -> None:
    payload = {
        "status": state.status,
        "completed_stages": state.completed_stages,
        "next_stage": state.next_stage,
        "updated_at": utc_now(),
    }
    progress_path(workspace).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def append_log(path: Path, message: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{utc_now()} {message}\n")


def next_stage_after(completed_stages: list[str]) -> str | None:
    if len(completed_stages) >= len(STAGES):
        return None
    return STAGES[len(completed_stages)]


def mark_stage_complete(workspace: Path, state: RunState, stage: str) -> RunState:
    if stage in state.completed_stages:
        return state

    completed = [*state.completed_stages, stage]
    next_stage = next_stage_after(completed)
    updated = RunState(
        status="complete" if next_stage is None else "running",
        completed_stages=completed,
        next_stage=next_stage,
    )
    append_log(workspace / "progress.log", f"completed {stage}")
    save_state(workspace, updated)
    return updated


def read_plan(workspace: Path) -> None:
    plan = {
        "goal": "Demonstrate a resumable agent task harness.",
        "stages": STAGES,
        "success": "A final verdict.json records pass/fail and evidence paths.",
    }
    (workspace / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def draft_change(workspace: Path) -> None:
    append_log(
        workspace / "decision.log",
        "decision: use files as durable context so a later run can resume safely",
    )
    (workspace / "draft.txt").write_text(
        "The agent would make a small, reviewable code change here.\n",
        encoding="utf-8",
    )


def run_validation(workspace: Path) -> None:
    artifacts = workspace / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "validation.txt").write_text(
        "validation: progress.json exists, decision.log exists, draft.txt exists\n",
        encoding="utf-8",
    )


def build_verdict(workspace: Path) -> dict:
    checks = [
        {"name": "progress_file_exists", "passed": progress_path(workspace).exists()},
        {"name": "decision_log_exists", "passed": (workspace / "decision.log").exists()},
        {
            "name": "validation_artifact_exists",
            "passed": (workspace / "artifacts" / "validation.txt").exists(),
        },
    ]
    return {
        "status": "pass" if all(check["passed"] for check in checks) else "fail",
        "checks": checks,
        "resume_supported": True,
        "evidence": {
            "progress": "progress.json",
            "progress_log": "progress.log",
            "decision_log": "decision.log",
            "validation": "artifacts/validation.txt",
        },
        "written_at": utc_now(),
    }


def write_verdict(workspace: Path) -> None:
    verdict = build_verdict(workspace)
    (workspace / "verdict.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


STAGE_HANDLERS: dict[str, Callable[[Path], None]] = {
    "read_plan": read_plan,
    "draft_change": draft_change,
    "run_validation": run_validation,
    "write_verdict": write_verdict,
}


def run_harness(workspace: Path, stop_after: int | None) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    state = load_state(workspace)
    if state.next_stage is None:
        print("Run already complete")
        return 0

    if state.completed_stages:
        print(f"Resuming from stage: {state.next_stage}")
    else:
        print("Starting new harness run")

    completed_this_run = 0
    while state.next_stage is not None:
        stage = state.next_stage
        append_log(workspace / "progress.log", f"starting {stage}")
        STAGE_HANDLERS[stage](workspace)
        state = mark_stage_complete(workspace, state, stage)
        completed_this_run += 1

        if stop_after is not None and completed_this_run >= stop_after and state.next_stage:
            interrupted = RunState(
                status="interrupted",
                completed_stages=state.completed_stages,
                next_stage=state.next_stage,
            )
            save_state(workspace, interrupted)
            print(
                f"Simulated interruption after {completed_this_run} stage(s)",
                file=sys.stderr,
            )
            return 2

    verdict = build_verdict(workspace)
    print(f"Verdict: {verdict['status']}")
    return 0 if verdict["status"] == "pass" else 1


def show_status(workspace: Path) -> int:
    state = load_state(workspace)
    print(f"status: {state.status}")
    print(f"completed_stages: {', '.join(state.completed_stages) or '(none)'}")
    print(f"next_stage: {state.next_stage}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Harness Engineering demo: resumable progress plus verdict evidence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run or resume the demo task.")
    run_parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("runs/demo-task"),
        help="Directory used to store durable progress and evidence.",
    )
    run_parser.add_argument(
        "--stop-after",
        type=int,
        default=None,
        help="Simulate an interruption after N stages completed in this invocation.",
    )

    status_parser = subparsers.add_parser("status", help="Show saved run progress.")
    status_parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("runs/demo-task"),
        help="Directory used to store durable progress and evidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        if args.stop_after is not None and args.stop_after < 1:
            parser.error("--stop-after must be greater than 0")
        return run_harness(args.workspace, args.stop_after)
    if args.command == "status":
        return show_status(args.workspace)

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
