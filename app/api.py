"""FastAPI application: POST /research."""
from __future__ import annotations
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from app.graph import run_research
load_dotenv()

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User research question")

class ResearchResponse(BaseModel):
    query: str
    report: str = Field(..., description="Final markdown report")
    errors: list[str] = Field(default_factory=list)
    current_agent: str = ""

def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Agent Research Assistant",
        version="0.1.0",
        description="LangGraph pipeline: search → summarize → critic → report (Groq LLM).",
    )
    origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins if o.strip()] or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    def root():
        return """
        <html>
            <head>
                <title>Multi-Agent Research Assistant</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body {
                        font-family: Arial, sans-serif;
                        background: #0f0f0f;
                        color: #fff;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        flex-direction: column;
                        gap: 16px;
                    }
                    h1 { color: #00ff88; font-size: 2rem; text-align: center; }
                    p { color: #aaa; font-size: 1rem; text-align: center; }
                    .pipeline {
                        background: #1a1a1a;
                        border: 1px solid #333;
                        padding: 12px 24px;
                        border-radius: 10px;
                        color: #00ff88;
                        font-size: 0.9rem;
                        letter-spacing: 1px;
                    }
                    .badges {
                        display: flex;
                        gap: 10px;
                        flex-wrap: wrap;
                        justify-content: center;
                    }
                    .badge {
                        background: #1a1a1a;
                        border: 1px solid #444;
                        padding: 6px 14px;
                        border-radius: 20px;
                        font-size: 0.8rem;
                        color: #ccc;
                    }
                    .btn {
                        background: #00ff88;
                        color: #000;
                        padding: 14px 32px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-weight: bold;
                        font-size: 1rem;
                        margin-top: 10px;
                        transition: background 0.2s;
                    }
                    .btn:hover { background: #00cc66; }
                </style>
            </head>
            <body>
                <h1>🤖 Multi-Agent Research Assistant</h1>
                <p>An autonomous AI pipeline that researches, summarizes, critiques, and reports.</p>
                <div class="pipeline">
                    Search → Summarize → Critic → Report
                </div>
                <div class="badges">
                    <span class="badge">⚡ Groq LLM</span>
                    <span class="badge">🦙 Llama 3</span>
                    <span class="badge">🔗 LangGraph</span>
                    <span class="badge">🚀 FastAPI</span>
                </div>
                <a class="btn" href="/docs">Launch API →</a>
            </body>
        </html>
        """

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/research", response_model=ResearchResponse)
    def research(req: ResearchRequest):
        if not os.environ.get("GROQ_API_KEY"):
            raise HTTPException(
                status_code=503,
                detail="GROQ_API_KEY is not configured on the server.",
            )
        q = req.query.strip()
        if not q:
            raise HTTPException(status_code=400, detail="Query must not be empty.")
        out = run_research(q)
        return ResearchResponse(
            query=q,
            report=out.get("final_report") or "",
            errors=list(out.get("errors") or []),
            current_agent=str(out.get("current_agent") or ""),
        )

    return app

app = create_app()
