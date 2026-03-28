"""FastAPI application: POST /research."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
