"""LangGraph orchestration: sequential agents with shared state."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents import critic_node, report_node, search_node, summarizer_node
from app.state import ResearchState


def build_research_graph():
    """Compile the sequential research pipeline as a LangGraph."""
    graph = StateGraph(ResearchState)
    graph.add_node("search", search_node)
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("report", report_node)
    graph.add_edge(START, "search")
    graph.add_edge("search", "summarizer")
    graph.add_edge("summarizer", "critic")
    graph.add_edge("critic", "report")
    graph.add_edge("report", END)
    return graph.compile()


_COMPILED = None


def get_compiled_graph():
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_research_graph()
    return _COMPILED


def initial_state(query: str, progress_hook: Callable[[str], None] | None = None) -> ResearchState:
    """Default state for a new research run."""
    s: ResearchState = {
        "query": query.strip(),
        "search_results": [],
        "summaries": [],
        "critic_output": {"contradictions": [], "assessments": []},
        "final_report": "",
        "errors": [],
        "current_agent": "",
    }
    if progress_hook is not None:
        s["_progress_hook"] = progress_hook
    return s


def run_research(
    query: str,
    progress_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """
    Execute the full pipeline. Returns the final graph state as a dict.
    Nodes call ``progress_hook`` with agent ids; streaming uses ``values`` for the final state.
    """
    graph = get_compiled_graph()
    state = initial_state(query, progress_hook=progress_hook)
    final_state: dict[str, Any] | None = None
    for chunk in graph.stream(state, stream_mode="values"):
        if isinstance(chunk, dict):
            final_state = dict(chunk)
    if final_state is None:
        return dict(state)
    return final_state
