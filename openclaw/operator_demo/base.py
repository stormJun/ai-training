from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from .schemas import OperatorContext
from .storage import InMemoryDatasetStore

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class Operator(ABC, Generic[InputT, OutputT]):
    name: ClassVar[str]
    version: ClassVar[str]
    description: ClassVar[str]
    input_model: ClassVar[type[InputT]]
    output_model: ClassVar[type[OutputT]]
    required_permissions: ClassVar[list[str]] = []

    def __init__(self, store: InMemoryDatasetStore) -> None:
        self.store = store

    @abstractmethod
    def run(self, data: InputT, ctx: OperatorContext) -> OutputT:
        pass
