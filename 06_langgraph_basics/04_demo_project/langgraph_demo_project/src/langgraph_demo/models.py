"""演示项目共享的数据模型。"""

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """所有代理服务统一使用的请求体。"""

    query: str = Field(..., description="发送给代理的用户问题。")


class AgentResponse(BaseModel):
    """所有代理统一返回的标准响应结构。"""

    agent: str
    status: str = "completed"
    summary: str
    detail: str


class StockRecord(BaseModel):
    """演示项目中使用的静态股票数据。"""

    code: str
    name: str
    sector: str
    close_price: float
    price_change_pct: float
    revenue_growth_pct: float
    pe_ratio: float
    volatility_pct: float
