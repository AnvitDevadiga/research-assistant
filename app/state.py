"""Shared LangGraph state for the research pipeline."""

from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict


class SearchHit(TypedDict):
    """One search result with URL and text used downstream."""

    url: str
    title: str
    snippet: str
    raw_content: str


class SourceSummary(TypedDict):
    """Structured summary for a single source."""

    url: str
    title: str
    summary: str
    key_facts: list[str]


class ClaimAssessment(TypedDict):
    """Per-claim confidence from the critic."""

    claim: str
    confidence: str  # high | medium | low
    notes: str


class CriticOutput(TypedDict):
    """Output of the critic agent."""

    contradictions: list[str]
    assessments: list[ClaimAssessment]


class ResearchState(TypedDict, total=False):
    """
    Graph state. Lists that accumulate failures use Annotated reducers.
    """

    query: str
    search_results: list[SearchHit]
    summaries: list[SourceSummary]
    critic_output: CriticOutput
    final_report: str
    errors: Annotated[list[str], operator.add]
    current_agent: str
    # Optional callback for Streamlit / external progress (not merged by graph)
    _progress_hook: NotRequired[Any]
