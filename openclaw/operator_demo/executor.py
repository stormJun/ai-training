from __future__ import annotations

from time import perf_counter
from typing import Any

from pydantic import BaseModel

from .registry import OperatorRegistry
from .schemas import ExecutionStep, OperatorContext
from .storage import InMemoryDatasetStore


class OperatorExecutor:
    def __init__(self, registry: OperatorRegistry, store: InMemoryDatasetStore) -> None:
        self.registry = registry
        self.store = store
        self.history: list[ExecutionStep] = []

    def execute(
        self,
        name: str,
        version: str,
        payload: dict[str, Any],
        ctx: OperatorContext,
    ) -> BaseModel:
        spec = self.registry.get(name, version)
        op_cls = spec.op_cls
        input_data = op_cls.input_model.model_validate(payload)

        started = perf_counter()
        try:
            output = op_cls(self.store).run(input_data, ctx)
            output = op_cls.output_model.model_validate(output)
            duration_ms = round((perf_counter() - started) * 1000, 2)
            self.history.append(
                ExecutionStep(
                    operator=name,
                    version=version,
                    status="success",
                    duration_ms=duration_ms,
                    message="执行成功",
                    metrics=getattr(output, "metrics", {}) or {},
                )
            )
            return output
        except Exception:
            duration_ms = round((perf_counter() - started) * 1000, 2)
            self.history.append(
                ExecutionStep(
                    operator=name,
                    version=version,
                    status="failed",
                    duration_ms=duration_ms,
                    message="执行失败",
                )
            )
            raise
