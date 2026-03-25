"""FastAPI app exposing the stock subagent."""

from fastapi import FastAPI

from ..models import AgentRequest, AgentResponse
from ..stock_agent import run_stock_agent


app = FastAPI(title="Week04 Stock Subagent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""

    return {"status": "ok"}


@app.post("/invoke", response_model=AgentResponse)
def invoke(request: AgentRequest) -> AgentResponse:
    """Run the stock subagent."""

    return run_stock_agent(request.query)
