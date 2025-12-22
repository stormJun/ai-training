from typing import List, TypedDict, Any


class AgentState(TypedDict, total=False):
    """State shared across LangGraph nodes."""

    topic: str
    style: str
    length: int
    research_report: str
    draft: str
    review_suggestions: str
    final_article: str
    log: List[str]
    search_sources: List[Any]
    log_research: str
    log_draft: str
    log_review: str
    log_polish: str
