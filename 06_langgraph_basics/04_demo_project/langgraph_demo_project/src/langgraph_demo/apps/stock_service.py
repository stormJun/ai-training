"""对外暴露股票查询子代理的 FastAPI 应用。"""

from fastapi import FastAPI

from ..models import AgentRequest, AgentResponse
from ..stock_agent import run_stock_agent


app = FastAPI(title="工作流编排 Stock Subagent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查接口。"""

    return {"status": "ok"}


@app.post("/invoke", response_model=AgentResponse)
def invoke(request: AgentRequest) -> AgentResponse:
    """执行股票查询子代理。"""

    return run_stock_agent(request.query)
