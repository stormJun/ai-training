"""Static stock repository used by all agents."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import StockRecord


DATA_FILE = Path(__file__).resolve().parent / "data" / "stocks.json"


@lru_cache(maxsize=1)
def load_records() -> list[StockRecord]:
    """Load the bundled demo dataset once."""

    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return [StockRecord.model_validate(item) for item in raw]


def get_stock_by_identifier(identifier: str) -> StockRecord | None:
    """Find a stock by code or company name."""

    needle = identifier.strip()
    if not needle:
        return None
    for record in load_records():
        if record.code == needle or record.name == needle:
            return record
    return None


def list_stock_mentions(query: str) -> list[StockRecord]:
    """Return all stocks mentioned in a query."""

    found: list[StockRecord] = []
    seen: set[str] = set()
    for record in load_records():
        if record.code in query or record.name in query:
            if record.code not in seen:
                found.append(record)
                seen.add(record.code)
    return found
