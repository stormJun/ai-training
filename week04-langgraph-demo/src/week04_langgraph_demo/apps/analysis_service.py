"""FastAPI app exposing the analysis subagent."""

from fastapi import FastAPI

from ..analysis_agent import run_analysis_agent
from ..models import AgentRequest, AgentResponse


app = FastAPI(title="Week04 Analysis Subagent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""

    return {"status": "ok"}


@app.post("/invoke", response_model=AgentResponse)
def invoke(request: AgentRequest) -> AgentResponse:
    """Run the analysis subagent."""

    return run_analysis_agent(request.query)
