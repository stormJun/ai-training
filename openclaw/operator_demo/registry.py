from __future__ import annotations

from dataclasses import dataclass

from .base import Operator


@dataclass(frozen=True)
class OperatorSpec:
    name: str
    version: str
    description: str
    input_schema: dict
    output_schema: dict
    op_cls: type[Operator]

    def to_public_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


class OperatorRegistry:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], OperatorSpec] = {}

    def register(self, op_cls: type[Operator]) -> None:
        spec = OperatorSpec(
            name=op_cls.name,
            version=op_cls.version,
            description=op_cls.description,
            input_schema=op_cls.input_model.model_json_schema(),
            output_schema=op_cls.output_model.model_json_schema(),
            op_cls=op_cls,
        )
        self._items[(spec.name, spec.version)] = spec

    def get(self, name: str, version: str) -> OperatorSpec:
        return self._items[(name, version)]

    def list(self) -> list[OperatorSpec]:
        return sorted(self._items.values(), key=lambda item: item.name)
