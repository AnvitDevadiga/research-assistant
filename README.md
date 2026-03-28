# Multi-Agent Research Assistant

A LangGraph-powered multi-agent pipeline that autonomously researches any topic using 4 specialized agents.

## Agents
- **Search Agent** — Finds relevant sources via DuckDuckGo
- **Summarizer Agent** — Extracts key information from sources
- **Critic Agent** — Cross-checks facts and flags contradictions
- **Report Agent** — Compiles structured markdown report

## Tech Stack
Python, LangGraph, LangChain, FastAPI, Groq (Llama 3), DuckDuckGo Search, Streamlit, Render.com

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your GROQ_API_KEY
streamlit run streamlit_app.py
```
