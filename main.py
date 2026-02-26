import os
# Load .env before anything else — must come first so all subsequent imports
# (agents.py, tools.py, crewai) pick up the correct env vars, and so that
# .env values override any stale inherited process environment variables.
from dotenv import load_dotenv
load_dotenv(override=True)

import uuid
import time
import asyncio
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from crewai import Crew, Process
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from task import (
    verification,
    analyze_financial_document as analyze_task,
    investment_analysis,
    risk_assessment,
)

# ---------------------------------------------------------------------------
# Config — Pydantic Settings (Fix 8)
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    openai_api_key: str = ""
    llm_model: str = "openai/gpt-4o-mini"
    max_file_size_mb: int = 10
    api_key: str = ""          # Set API_KEY in .env to enable auth; leave blank to disable
    sentry_dsn: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

MAX_FILE_SIZE = settings.max_file_size_mb * 1024 * 1024

# ---------------------------------------------------------------------------
# Sentry (optional — only initialised when SENTRY_DSN is set)
# ---------------------------------------------------------------------------
if settings.sentry_dsn and settings.sentry_dsn.startswith("http"):
    import sentry_sdk
    sentry_sdk.init(dsn=settings.sentry_dsn)

# ---------------------------------------------------------------------------
# Structured logging (Fix 6)
# ---------------------------------------------------------------------------
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)
log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Rate limiting (Fix 5)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])

# ---------------------------------------------------------------------------
# API Key auth (Fix 4 — security)
# ---------------------------------------------------------------------------
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    """Validate X-API-Key header when API_KEY is configured in .env.
    If API_KEY is not set, auth is disabled (useful for local dev)."""
    if settings.api_key and key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

# ---------------------------------------------------------------------------
# Async context manager for temp file handling (Fix 7)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def temp_pdf(content: bytes):
    """Write uploaded bytes to a temp file, yield the path, then clean up."""
    os.makedirs("data", exist_ok=True)
    path = f"data/financial_document_{uuid.uuid4()}.pdf"
    try:
        with open(path, "wb") as f:
            f.write(content)
        yield path
    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass  # Ignore cleanup errors

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Financial Document Analyzer",
    description="AI-powered financial document analysis using CrewAI agents.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Max 5 requests/minute."})


# ---------------------------------------------------------------------------
# Crew runner
# ---------------------------------------------------------------------------
def run_crew(query: str, file_path: str) -> str:
    """Run the full multi-agent financial analysis crew (synchronous — called via asyncio.to_thread)."""
    financial_crew = Crew(
        agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
        tasks=[verification, analyze_task, investment_analysis, risk_assessment],
        process=Process.sequential,
        verbose=False,  # Fix 4: verbose=True adds overhead; set False for production
    )
    result = financial_crew.kickoff({"query": query, "file_path": file_path})
    return str(result)


# ---------------------------------------------------------------------------
# Input model (Fix — Pydantic validation on query)
# ---------------------------------------------------------------------------
class AnalysisQuery(BaseModel):
    query: str = Field(
        default="Analyze this financial document for investment insights",
        min_length=5,
        max_length=500,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Financial Document Analyzer API is running", "status": "healthy"}


@app.post("/analyze")
@limiter.limit("5/minute")
async def analyze_document(
    request: Request,                          # required by slowapi
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
    _: None = Security(verify_api_key),        # API key guard
):
    """Analyze a financial document (PDF) and return comprehensive AI-powered insights.

    - **file**: PDF financial document to analyze (required)
    - **query**: Specific question or analysis focus (optional, has default)
    - **X-API-Key**: Required header when API_KEY is set in .env
    """
    job_id = str(uuid.uuid4())

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Fix 4: File size limit — read once, check before saving
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {settings.max_file_size_mb}MB.",
        )

    # Validate and normalise query
    query = query.strip() if query and query.strip() else "Analyze this financial document for investment insights"
    try:
        AnalysisQuery(query=query)
    except Exception:
        raise HTTPException(status_code=422, detail="Query must be between 5 and 500 characters.")

    log.info("analysis_started", job_id=job_id, query=query, filename=file.filename)
    start = time.time()

    try:
        async with temp_pdf(content) as file_path:          # Fix 7: context manager handles cleanup
            response = await asyncio.to_thread(run_crew, query=query, file_path=file_path)

        duration = round(time.time() - start, 2)
        log.info("analysis_complete", job_id=job_id, duration_seconds=duration)  # Fix 6: timing log

        return {
            "status": "success",
            "job_id": job_id,
            "query": query,
            "analysis": response,
            "file_processed": file.filename,
            "duration_seconds": duration,
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error("analysis_failed", job_id=job_id, error=str(e))  # Fix 6: structured error log
        raise HTTPException(
            status_code=500,
            detail=f"Error processing financial document: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
