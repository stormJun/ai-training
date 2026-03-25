from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import AgentNodes


def create_graph(mcp_tools):
    """Build a linear LangGraph: research -> write -> review -> polish."""
    nodes = AgentNodes(mcp_tools)
    workflow = StateGraph(AgentState)
    workflow.add_node("research", nodes.research_node)
    workflow.add_node("write", nodes.writing_node)
    workflow.add_node("review", nodes.review_node)
    workflow.add_node("polish", nodes.polishing_node)

    workflow.set_entry_point("research")
    workflow.add_edge("research", "write")
    workflow.add_edge("write", "review")
    workflow.add_edge("review", "polish")
    workflow.add_edge("polish", END)
    return workflow.compile()
