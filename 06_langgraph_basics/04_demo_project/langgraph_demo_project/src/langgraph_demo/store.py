"""供所有代理共享使用的静态股票数据仓库。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import StockRecord


DATA_FILE = Path(__file__).resolve().parent / "data" / "stocks.json"


@lru_cache(maxsize=1)
def load_records() -> list[StockRecord]:
    """一次性加载打包在项目内的演示数据集。"""

    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return [StockRecord.model_validate(item) for item in raw]


def get_stock_by_identifier(identifier: str) -> StockRecord | None:
    """根据股票代码或公司名称查找股票。"""

    needle = identifier.strip()
    if not needle:
        return None
    for record in load_records():
        if record.code == needle or record.name == needle:
            return record
    return None


def list_stock_mentions(query: str) -> list[StockRecord]:
    """返回问题中提到的全部股票。"""

    found: list[StockRecord] = []
    seen: set[str] = set()
    for record in load_records():
        if record.code in query or record.name in query:
            if record.code not in seen:
                found.append(record)
                seen.add(record.code)
    return found
