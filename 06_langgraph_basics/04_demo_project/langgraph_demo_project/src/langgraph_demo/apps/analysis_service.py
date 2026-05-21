"""对外暴露分析子代理的 FastAPI 应用。"""

from fastapi import FastAPI

from ..analysis_agent import run_analysis_agent
from ..models import AgentRequest, AgentResponse


app = FastAPI(title="工作流编排 Analysis Subagent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查接口。"""

    return {"status": "ok"}


@app.post("/invoke", response_model=AgentResponse)
def invoke(request: AgentRequest) -> AgentResponse:
    """执行分析子代理。"""

    return run_analysis_agent(request.query)
