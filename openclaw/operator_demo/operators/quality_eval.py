from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..base import Operator
from ..schemas import DatasetRef, OperatorContext


class QualityEvalInput(BaseModel):
    dataset: DatasetRef
    threshold: float = Field(default=0.8, ge=0, le=1)


class QualityEvalOutput(BaseModel):
    score: float
    passed: bool
    metrics: dict[str, Any]
    issues: list[str] = Field(default_factory=list)


class QualityEvalOperator(Operator[QualityEvalInput, QualityEvalOutput]):
    name = "quality_eval"
    version = "1.0.0"
    description = "评估数据集重复率、空值率和综合质量分"
    input_model = QualityEvalInput
    output_model = QualityEvalOutput
    required_permissions = ["dataset:read"]

    def run(self, data: QualityEvalInput, ctx: OperatorContext) -> QualityEvalOutput:
        rows = self.store.get_rows(data.dataset.dataset_id)
        total_rows = len(rows)
        total_cells = max(total_rows * max(len(data.dataset.columns), 1), 1)

        seen: set[tuple[tuple[str, str], ...]] = set()
        duplicate_count = 0
        empty_cells = 0
        for row in rows:
            key = tuple(sorted((str(k), str(v)) for k, v in row.items()))
            if key in seen:
                duplicate_count += 1
            seen.add(key)
            empty_cells += sum(1 for value in row.values() if str(value).strip() == "")

        duplicate_rate = round(duplicate_count / max(total_rows, 1), 4)
        null_rate = round(empty_cells / total_cells, 4)
        score = round(max(0.0, 1 - duplicate_rate * 0.5 - null_rate * 0.5), 4)
        passed = score >= data.threshold
        issues: list[str] = []

        if duplicate_rate > 0:
            issues.append("存在重复数据")
        if null_rate > 0.2:
            issues.append("空值率过高")
        if not passed:
            issues.append("综合质量分未达到门禁阈值")

        return QualityEvalOutput(
            score=score,
            passed=passed,
            metrics={
                "total_rows": total_rows,
                "duplicate_rate": duplicate_rate,
                "null_rate": null_rate,
                "threshold": data.threshold,
            },
            issues=issues,
        )
