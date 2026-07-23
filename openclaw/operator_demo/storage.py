from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .schemas import DatasetRef


@dataclass
class DatasetRecord:
    ref: DatasetRef
    rows: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


class InMemoryDatasetStore:
    def __init__(self) -> None:
        self._datasets: dict[str, DatasetRecord] = {}

    def put(
        self,
        dataset_id: str,
        rows: list[dict[str, Any]],
        uri: str,
        columns: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> DatasetRef:
        ref = DatasetRef(
            dataset_id=dataset_id,
            uri=uri,
            columns=columns,
        )
        self._datasets[dataset_id] = DatasetRecord(
            ref=ref,
            rows=deepcopy(rows),
            metadata=metadata or {},
        )
        return ref

    def get_rows(self, dataset_id: str) -> list[dict[str, Any]]:
        record = self._datasets[dataset_id]
        return deepcopy(record.rows)

    def get_ref(self, dataset_id: str) -> DatasetRef:
        return self._datasets[dataset_id].ref

    def list(self) -> list[DatasetRecord]:
        return list(self._datasets.values())
