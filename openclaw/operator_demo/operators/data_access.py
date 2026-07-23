from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ..base import Operator
from ..schemas import DatasetRef, OperatorContext

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class DataAccessInput(BaseModel):
    dataset_id: str = "users_raw"
    source_type: Literal["csv"] = "csv"
    source_path: str = "data/users.csv"


class DataAccessOutput(BaseModel):
    dataset: DatasetRef
    rows_loaded: int
    columns: list[str]
    preview: list[dict]
    metrics: dict = Field(default_factory=dict)


class DataAccessOperator(Operator[DataAccessInput, DataAccessOutput]):
    name = "data_access"
    version = "1.0.0"
    description = "从 CSV 文件接入数据，并生成平台内部数据集引用"
    input_model = DataAccessInput
    output_model = DataAccessOutput
    required_permissions = ["dataset:write"]

    def run(self, data: DataAccessInput, ctx: OperatorContext) -> DataAccessOutput:
        source_path = Path(data.source_path)
        if not source_path.is_absolute():
            source_path = PACKAGE_ROOT / source_path

        with source_path.open("r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            rows = [dict(row) for row in reader]
            columns = reader.fieldnames or []

        dataset = self.store.put(
            dataset_id=data.dataset_id,
            rows=rows,
            uri=str(source_path),
            columns=columns,
            metadata={"source": data.source_type, "created_by": ctx.source},
        )

        return DataAccessOutput(
            dataset=dataset,
            rows_loaded=len(rows),
            columns=columns,
            preview=rows[:5],
            metrics={"rows_loaded": len(rows)},
        )
