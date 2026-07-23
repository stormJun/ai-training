from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .executor import OperatorExecutor
from .operators import CleanOperator, DataAccessOperator, QualityEvalOperator
from .registry import OperatorRegistry
from .schemas import OperatorContext, SourceType, WorkflowRunResult
from .storage import InMemoryDatasetStore
from .workflow import WorkflowRunner, default_workflow


@dataclass
class DemoRuntime:
    registry: OperatorRegistry
    store: InMemoryDatasetStore
    executor: OperatorExecutor

    def context(self, source: SourceType = "ui") -> OperatorContext:
        return OperatorContext(run_id=str(uuid4()), source=source)

    def run_default_workflow(self, source: SourceType = "ui") -> WorkflowRunResult:
        runner = WorkflowRunner(self.executor)
        return runner.run(default_workflow(), self.context(source=source))


def create_demo_runtime() -> DemoRuntime:
    store = InMemoryDatasetStore()
    registry = OperatorRegistry()
    registry.register(DataAccessOperator)
    registry.register(CleanOperator)
    registry.register(QualityEvalOperator)
    executor = OperatorExecutor(registry=registry, store=store)
    return DemoRuntime(registry=registry, store=store, executor=executor)
