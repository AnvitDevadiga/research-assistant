"""
Streamlit UI: query, live agent progress, final markdown report.

Run from repo root: ``streamlit run streamlit_app.py``
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

USE_API = os.environ.get("STREAMLIT_USE_API", "").lower() in ("1", "true", "yes")
API_BASE = os.environ.get("RESEARCH_API_URL", "http://127.0.0.1:8000").rstrip("/")


def run_local_pipeline(query: str, status_ph) -> dict:
    """Run LangGraph in-process so progress hooks can update the UI."""
    from app.graph import run_research

    order = ["search", "summarizer", "critic", "report"]
    labels = {
        "search": "1. Search (DuckDuckGo)",
        "summarizer": "2. Summarizer",
        "critic": "3. Critic",
        "report": "4. Report",
    }

    def hook(agent: str) -> None:
        if agent not in order:
            return
        idx = order.index(agent)
        lines: list[str] = []
        for i, key in enumerate(order):
            if i < idx:
                lines.append(f"✅ {labels[key]}")
            elif i == idx:
                lines.append(f"🔄 **{labels[key]}** — running")
            else:
                lines.append(f"⏳ {labels[key]} — pending")
        status_ph.markdown("\n\n".join(lines))

    out = run_research(query, progress_hook=hook)
    done_lines = [f"✅ {labels[k]}" for k in order]
    status_ph.markdown("\n\n".join(done_lines))
    return out


def run_remote_api(query: str) -> dict:
    r = requests.post(
        f"{API_BASE}/research",
        json={"query": query},
        timeout=600,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "final_report": data.get("report", ""),
        "errors": data.get("errors", []),
        "current_agent": data.get("current_agent", ""),
    }


st.set_page_config(page_title="Research Assistant", layout="wide")
st.title("Multi-agent research assistant")
st.caption("LangGraph pipeline · Groq · DuckDuckGo")

with st.sidebar:
    st.markdown("**Mode**")
    if USE_API:
        st.info(f"Using API: `{API_BASE}`")
    else:
        st.info("Running the graph **in-process** (best for live progress).")
        st.markdown("Set `STREAMLIT_USE_API=1` and `RESEARCH_API_URL` to call FastAPI instead.")

query = st.text_input("Research query", placeholder="e.g. Latest trends in solid-state batteries")

if st.button("Run research", type="primary"):
    if not query.strip():
        st.warning("Enter a query.")
    elif not USE_API and not os.environ.get("GROQ_API_KEY"):
        st.error("Set the `GROQ_API_KEY` environment variable (e.g. in `.env`).")
    else:
        status_ph = st.empty()
        report_ph = st.container()
        with st.spinner("Running pipeline…"):
            try:
                if USE_API:
                    status_ph.info(f"Calling `{API_BASE}/research` …")
                    out = run_remote_api(query.strip())
                else:
                    out = run_local_pipeline(query.strip(), status_ph)
            except Exception as e:
                st.error(str(e))
                st.stop()
        errs = out.get("errors") or []
        if errs:
            with st.expander("Pipeline notices / partial failures", expanded=False):
                for e in errs:
                    st.caption(e)
        report_ph.markdown(out.get("final_report") or "_No report generated._")
