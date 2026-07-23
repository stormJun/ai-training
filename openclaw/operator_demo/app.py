from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .runtime import create_demo_runtime

PACKAGE_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_ROOT / "static"

app = FastAPI(title="算子化数据资产 Demo", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
runtime = create_demo_runtime()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/operators")
def list_operators() -> list[dict[str, Any]]:
    return [spec.to_public_dict() for spec in runtime.registry.list()]


@app.get("/operators/{name}/{version}")
def get_operator(name: str, version: str) -> dict[str, Any]:
    try:
        return runtime.registry.get(name, version).to_public_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="operator not found") from exc


@app.post("/operators/{name}/{version}/execute")
def execute_operator(
    name: str,
    version: str,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    try:
        output = runtime.executor.execute(
            name=name,
            version=version,
            payload=payload,
            ctx=runtime.context(source="api"),
        )
        return output.model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="operator not found") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@app.post("/workflows/default/run")
def run_default_workflow() -> dict[str, Any]:
    return runtime.run_default_workflow(source="ui").model_dump(mode="json")


@app.get("/runs/history")
def run_history() -> list[dict[str, Any]]:
    return [step.model_dump(mode="json") for step in runtime.executor.history]
