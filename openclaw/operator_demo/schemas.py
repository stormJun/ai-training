from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SourceType = Literal["ui", "api", "agent", "scheduler"]


class DatasetRef(BaseModel):
    dataset_id: str
    uri: str
    format: str = "table"
    columns: list[str] = Field(default_factory=list)
    version: str = "1.0.0"


class OperatorContext(BaseModel):
    run_id: str
    tenant_id: str = "demo"
    user_id: str = "demo-user"
    source: SourceType = "ui"
    trace_id: str | None = None


class ExecutionStep(BaseModel):
    node_id: str | None = None
    operator: str
    version: str
    status: Literal["success", "failed"]
    duration_ms: float
    message: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunResult(BaseModel):
    run_id: str
    status: Literal["success", "failed"]
    steps: list[ExecutionStep]
    outputs: dict[str, dict[str, Any]]
    lineage: list[dict[str, Any]]
    logs: list[str]
