"""Agent 3: Cross-check summaries, contradictions, confidence per claim."""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_chat_model
from app.state import ClaimAssessment, CriticOutput, ResearchState, SourceSummary


def _parse_critic_json(text: str) -> dict | None:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _empty_critic() -> CriticOutput:
    return {"contradictions": [], "assessments": []}


def _fallback_critic(summaries: list[SourceSummary]) -> CriticOutput:
    claims: list[ClaimAssessment] = []
    for s in summaries:
        for fact in (s.get("key_facts") or [])[:3]:
            claims.append(
                {
                    "claim": f"{s.get('title', '')}: {fact}",
                    "confidence": "low",
                    "notes": "Heuristic fallback — LLM critic unavailable.",
                }
            )
            if len(claims) >= 12:
                return {"contradictions": [], "assessments": claims}
    return {"contradictions": [], "assessments": claims}


def critic_node(state: ResearchState) -> dict:
    """Compare sources and flag contradictions and confidence."""
    hook = state.get("_progress_hook")
    if callable(hook):
        try:
            hook("critic")
        except Exception:
            pass

    summaries: list[SourceSummary] = state.get("summaries") or []
    if not summaries:
        return {
            "critic_output": _empty_critic(),
            "current_agent": "critic",
            "errors": [],
        }

    try:
        llm = get_chat_model()
        payload = [
            {
                "url": s["url"],
                "title": s.get("title", ""),
                "summary": s.get("summary", ""),
                "key_facts": s.get("key_facts", []),
            }
            for s in summaries
        ]
        sys = SystemMessage(
            content=(
                "You are a careful fact-checking critic. Compare the sources for "
                "contradictions or conflicting claims. Output ONLY valid JSON with keys: "
                '"contradictions" (array of strings describing conflicts between sources), '
                '"assessments" (array of objects with "claim" (string), "confidence" '
                '("high"|"medium"|"low"), "notes" (string)). '
                "Assess important factual claims from the summaries. No markdown outside JSON."
            )
        )
        human = HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2))
        out = llm.invoke([sys, human])
        text = out.content if hasattr(out, "content") else str(out)
        parsed = _parse_critic_json(text)
        if not parsed:
            return {
                "critic_output": _fallback_critic(summaries),
                "current_agent": "critic",
                "errors": ["Critic: failed to parse JSON; heuristic fallback used."],
            }
        contradictions = parsed.get("contradictions") or []
        if not isinstance(contradictions, list):
            contradictions = []
        contradictions = [str(c).strip() for c in contradictions if str(c).strip()]
        raw_assess = parsed.get("assessments") or []
        assessments: list[ClaimAssessment] = []
        if isinstance(raw_assess, list):
            for a in raw_assess:
                if not isinstance(a, dict):
                    continue
                conf = str(a.get("confidence", "medium")).lower()
                if conf not in ("high", "medium", "low"):
                    conf = "medium"
                assessments.append(
                    {
                        "claim": str(a.get("claim", "")).strip(),
                        "confidence": conf,
                        "notes": str(a.get("notes", "")).strip(),
                    }
                )
        return {
            "critic_output": {
                "contradictions": contradictions,
                "assessments": assessments,
            },
            "current_agent": "critic",
        }
    except Exception as e:
        return {
            "critic_output": _fallback_critic(summaries),
            "current_agent": "critic",
            "errors": [f"Critic agent failed: {e!s}; heuristic fallback used."],
        }
