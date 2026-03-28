"""Agent 2: Summarize each source with key facts."""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_chat_model
from app.state import ResearchState, SearchHit, SourceSummary


def _parse_json_array(text: str) -> list[dict]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _fallback_summary(hit: SearchHit) -> SourceSummary:
    snippet = hit.get("snippet") or hit.get("raw_content", "")[:800]
    return {
        "url": hit["url"],
        "title": hit.get("title", ""),
        "summary": snippet[:2000],
        "key_facts": [snippet[:240]] if snippet else [],
    }


def summarizer_node(state: ResearchState) -> dict:
    """Produce structured summaries for each search hit."""
    hook = state.get("_progress_hook")
    if callable(hook):
        try:
            hook("summarizer")
        except Exception:
            pass

    hits: list[SearchHit] = state.get("search_results") or []
    if not hits:
        return {
            "summaries": [],
            "current_agent": "summarizer",
            "errors": [],
        }

    llm = get_chat_model()
    summaries: list[SourceSummary] = []
    batch_errors: list[str] = []

    for hit in hits:
        try:
            content = (hit.get("raw_content") or hit.get("snippet") or "")[:12000]
            sys = SystemMessage(
                content=(
                    "You extract concise summaries and key facts from web text. "
                    "Respond with ONLY valid JSON: an array of one object with keys "
                    '"summary" (string, 2-4 sentences), "key_facts" (array of 3-7 short strings). '
                    "No markdown outside JSON."
                )
            )
            human = HumanMessage(
                content=f"URL: {hit['url']}\nTitle: {hit.get('title','')}\n\nText:\n{content}"
            )
            out = llm.invoke([sys, human])
            text = out.content if hasattr(out, "content") else str(out)
            parsed = _parse_json_array(text)
            obj = parsed[0] if parsed else {}
            summary_text = str(obj.get("summary", "")).strip()
            facts = obj.get("key_facts")
            if not isinstance(facts, list):
                facts = []
            facts = [str(f).strip() for f in facts if str(f).strip()]
            if not summary_text and not facts:
                summaries.append(_fallback_summary(hit))
                batch_errors.append(
                    f"Summarizer: JSON parse empty for {hit.get('url', '')}; used snippet fallback."
                )
            else:
                summaries.append(
                    {
                        "url": hit["url"],
                        "title": hit.get("title", ""),
                        "summary": summary_text or (facts[0] if facts else ""),
                        "key_facts": facts
                        if facts
                        else ([summary_text[:200]] if summary_text else []),
                    }
                )
        except Exception as e:
            summaries.append(_fallback_summary(hit))
            batch_errors.append(
                f"Summarizer failed for {hit.get('url', '')}: {e!s}; used snippet fallback."
            )

    out: dict = {"summaries": summaries, "current_agent": "summarizer"}
    if batch_errors:
        out["errors"] = batch_errors
    return out
