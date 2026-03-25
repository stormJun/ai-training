"""Shared data models for the demo."""

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request payload for all agent services."""

    query: str = Field(..., description="User input sent to an agent.")


class AgentResponse(BaseModel):
    """Normalized response returned by all agents."""

    agent: str
    status: str = "completed"
    summary: str
    detail: str


class StockRecord(BaseModel):
    """Static stock data used by the demo."""

    code: str
    name: str
    sector: str
    close_price: float
    price_change_pct: float
    revenue_growth_pct: float
    pe_ratio: float
    volatility_pct: float
