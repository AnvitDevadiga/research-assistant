"""Agent 4: Final markdown report."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_chat_model
from app.state import ResearchState


def _minimal_report(state: ResearchState) -> str:
    q = state.get("query", "")
    lines = [
        "## Overview",
        f"Research query: **{q}**",
        "",
        "## Key Findings",
        "_No summarized sources available._",
        "",
        "## Contradictions Found",
        "_No critic output._",
        "",
        "## Sources",
        "_None._",
    ]
    return "\n".join(lines)


def report_node(state: ResearchState) -> dict:
    """Synthesize verified material into structured markdown."""
    hook = state.get("_progress_hook")
    if callable(hook):
        try:
            hook("report")
        except Exception:
            pass

    try:
        llm = get_chat_model()
        sys = SystemMessage(
            content=(
                "You write clear research reports in Markdown. Required sections with these "
                "exact headings (use ##): Overview, Key Findings, Contradictions Found, Sources. "
                "Under Sources, list each URL as a bullet with title. "
                "Integrate the summaries and critic JSON provided. Be concise."
            )
        )
        bundle = {
            "query": state.get("query", ""),
            "summaries": state.get("summaries", []),
            "critic": state.get("critic_output", {}),
            "pipeline_errors": state.get("errors", []),
        }
        human = HumanMessage(
            content=(
                "Produce the final report from this JSON:\n\n"
                f"{json.dumps(bundle, ensure_ascii=False, indent=2)}"
            )
        )
        out = llm.invoke([sys, human])
        text = (out.content if hasattr(out, "content") else str(out)).strip()
        if not text:
            return {
                "final_report": _minimal_report(state),
                "current_agent": "report",
                "errors": ["Report: empty LLM output; minimal report generated."],
            }
        return {"final_report": text, "current_agent": "report"}
    except Exception as e:
        return {
            "final_report": _minimal_report(state),
            "current_agent": "report",
            "errors": [f"Report agent failed: {e!s}; minimal report generated."],
        }
