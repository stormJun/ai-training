from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .executor import OperatorExecutor
from .schemas import OperatorContext, WorkflowRunResult


class WorkflowNode(BaseModel):
    id: str
    operator: str
    version: str
    input: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    from_node: str
    to_node: str
    output_key: str
    input_key: str


class WorkflowDefinition(BaseModel):
    name: str
    version: str
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge] = Field(default_factory=list)


class WorkflowRunner:
    def __init__(self, executor: OperatorExecutor) -> None:
        self.executor = executor

    def run(self, workflow: WorkflowDefinition, ctx: OperatorContext) -> WorkflowRunResult:
        outputs: dict[str, dict[str, Any]] = {}
        lineage: list[dict[str, Any]] = []
        logs: list[str] = []
        start_index = len(self.executor.history)

        try:
            for node in workflow.nodes:
                payload = dict(node.input)
                for edge in workflow.edges:
                    if edge.to_node != node.id:
                        continue
                    from_output = outputs[edge.from_node]
                    payload[edge.input_key] = from_output[edge.output_key]

                output_model = self.executor.execute(
                    name=node.operator,
                    version=node.version,
                    payload=payload,
                    ctx=ctx,
                )
                output = output_model.model_dump(mode="json")
                outputs[node.id] = output

                step = self.executor.history[-1].model_copy(update={"node_id": node.id})
                self.executor.history[-1] = step
                logs.append(f"{node.id}: {node.operator}@{node.version} 执行成功")
                lineage.append(
                    {
                        "node_id": node.id,
                        "operator": node.operator,
                        "version": node.version,
                        "input_keys": sorted(payload.keys()),
                        "output_keys": sorted(output.keys()),
                    }
                )

            steps = self.executor.history[start_index:]
            return WorkflowRunResult(
                run_id=ctx.run_id,
                status="success",
                steps=steps,
                outputs=outputs,
                lineage=lineage,
                logs=logs,
            )
        except Exception as exc:
            steps = self.executor.history[start_index:]
            logs.append(f"工作流失败: {exc}")
            return WorkflowRunResult(
                run_id=ctx.run_id,
                status="failed",
                steps=steps,
                outputs=outputs,
                lineage=lineage,
                logs=logs,
            )


def default_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="demo_data_asset_pipeline",
        version="1.0.0",
        nodes=[
            WorkflowNode(
                id="access_users",
                operator="data_access",
                version="1.0.0",
                input={
                    "dataset_id": "users_raw",
                    "source_path": "data/users.csv",
                },
            ),
            WorkflowNode(
                id="clean_users",
                operator="clean",
                version="1.0.0",
                input={
                    "rules": ["deduplicate", "drop_empty_name", "mask_phone"],
                },
            ),
            WorkflowNode(
                id="score_users",
                operator="quality_eval",
                version="1.0.0",
                input={
                    "threshold": 0.8,
                },
            ),
        ],
        edges=[
            WorkflowEdge(
                from_node="access_users",
                to_node="clean_users",
                output_key="dataset",
                input_key="dataset",
            ),
            WorkflowEdge(
                from_node="clean_users",
                to_node="score_users",
                output_key="cleaned_dataset",
                input_key="dataset",
            ),
        ],
    )
