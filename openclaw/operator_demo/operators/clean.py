from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from ..base import Operator
from ..schemas import DatasetRef, OperatorContext


class CleanInput(BaseModel):
    dataset: DatasetRef
    rules: list[str] = Field(default_factory=lambda: ["deduplicate", "drop_empty_name", "mask_phone"])


class CleanOutput(BaseModel):
    cleaned_dataset: DatasetRef
    removed_rows: int
    changed_rows: int
    preview: list[dict[str, Any]]
    metrics: dict[str, Any] = Field(default_factory=dict)


class CleanOperator(Operator[CleanInput, CleanOutput]):
    name = "clean"
    version = "1.0.0"
    description = "对数据集执行去重、空值过滤和手机号脱敏"
    input_model = CleanInput
    output_model = CleanOutput
    required_permissions = ["dataset:read", "dataset:write"]

    def run(self, data: CleanInput, ctx: OperatorContext) -> CleanOutput:
        rows = self.store.get_rows(data.dataset.dataset_id)
        original_count = len(rows)

        cleaned = rows
        removed_rows = 0

        if "deduplicate" in data.rules:
            deduplicated: list[dict[str, Any]] = []
            seen: set[tuple[tuple[str, str], ...]] = set()
            for row in cleaned:
                key = tuple(sorted((str(k), str(v)) for k, v in row.items()))
                if key in seen:
                    removed_rows += 1
                    continue
                seen.add(key)
                deduplicated.append(row)
            cleaned = deduplicated

        if "drop_empty_name" in data.rules:
            filtered = [row for row in cleaned if str(row.get("name", "")).strip()]
            removed_rows += len(cleaned) - len(filtered)
            cleaned = filtered

        changed_rows = 0
        if "mask_phone" in data.rules:
            masked: list[dict[str, Any]] = []
            for row in cleaned:
                next_row = dict(row)
                phone = str(next_row.get("phone", "")).strip()
                if re.fullmatch(r"\d{7,}", phone):
                    next_row["phone"] = f"{phone[:3]}****{phone[-4:]}"
                    changed_rows += 1
                masked.append(next_row)
            cleaned = masked

        cleaned_dataset = self.store.put(
            dataset_id=f"{data.dataset.dataset_id}_cleaned",
            rows=cleaned,
            uri=f"memory://{data.dataset.dataset_id}_cleaned",
            columns=data.dataset.columns,
            metadata={"source_dataset": data.dataset.dataset_id, "rules": data.rules},
        )

        return CleanOutput(
            cleaned_dataset=cleaned_dataset,
            removed_rows=removed_rows,
            changed_rows=changed_rows,
            preview=cleaned[:5],
            metrics={
                "input_rows": original_count,
                "output_rows": len(cleaned),
                "removed_rows": removed_rows,
                "changed_rows": changed_rows,
            },
        )
