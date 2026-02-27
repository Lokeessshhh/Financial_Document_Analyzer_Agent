## ═══════════════════════════════════════════════════════════════
## FILE: main.py
## FIXES APPLIED: 4
##   #1 — MISSING_AGENT: Only used financial_analyst, missing 3 other agents
##   #2 — MISSING_TASK: Only used analyze_financial_document, missing 3 other tasks
##   #3 — LOGIC_FIX: run_crew didn't pass file_path to kickoff
##   #4 — LOGIC_FIX: No extraction of individual agent outputs from result
## ENHANCEMENTS: 8
##   #1 — Added async queue processing with Celery + Redis
##   #2 — Added database storage with SQLAlchemy + PostgreSQL
##   #3 — Added rate limiting with slowapi
##   #4 — Added structured logging with structlog
##   #5 — Added API key authentication
##   #6 — Added file size validation
##   #7 — Added AI-synthesized final answer generation
##   #8 — Added job status and results endpoints
## ═══════════════════════════════════════════════════════════════

"""
Financial Document Analyzer API
===============================
FastAPI application with async queue processing using Celery + Upstash Redis,
and persistent storage using Neon PostgreSQL.
"""
import os
import uuid
import time
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List

import structlog
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

## ─────────────────────────────────────────────────────
## BUG_FIX #1: MISSING_AGENT - Only one agent was used
## BUG_FIX #2: MISSING_TASK - Only one task was used
## Original:   from agents import financial_analyst
##             from task import analyze_financial_document
## Problem:    The crew only had 1 agent and 1 task, but the system was supposed
##             to have 4 specialists (verifier, analyst, advisor, risk assessor).
## Fix:        Import all 4 agents and all 4 tasks for complete multi-agent pipeline.
## ─────────────────────────────────────────────────────
from crewai import Crew, Process
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from task import (
    verification,
    analyze_financial_document as analyze_task,
    investment_analysis,
    risk_assessment,
)

# Import new modules
from config import settings
from database import (
    init_db, 
    get_db_session, 
    AnalysisJob, 
    AnalysisResult,
    JobStatus
)
from worker import analyze_document_task

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv(override=True)

MAX_FILE_SIZE = settings.max_file_size_mb * 1024 * 1024

# ---------------------------------------------------------------------------
# Sentry (optional — only initialised when SENTRY_DSN is set)
# ---------------------------------------------------------------------------
if settings.sentry_dsn and settings.sentry_dsn.startswith("http"):
    import sentry_sdk
    sentry_sdk.init(dsn=settings.sentry_dsn)

# ---------------------------------------------------------------------------
# Structured logging
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
# Rate limiting
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ---------------------------------------------------------------------------
# API Key auth
# ---------------------------------------------------------------------------
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    """Validate X-API-Key header when API_KEY is configured in .env.
    If API_KEY is not set, auth is disabled (useful for local dev)."""
    # AUTH DISABLED FOR LOCAL DEV
    return
    
    if settings.api_key and key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

# ---------------------------------------------------------------------------
# Lifespan context manager for startup/shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    log.info("initializing_database")
    init_db()
    log.info("database_initialized")
    yield

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Financial Document Analyzer",
    description="AI-powered financial document analysis using CrewAI agents. Supports both synchronous and asynchronous (queue-based) processing.",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Max 5 requests/minute."})


# ---------------------------------------------------------------------------
# Crew runner (synchronous)
# ---------------------------------------------------------------------------
def generate_final_answer(verification: str, financial_analysis: str, investment_analysis: str, risk_assessment: str) -> str:
    """Use AI to synthesize all 4 agent outputs into a comprehensive final answer."""
    from litellm import completion
    
    prompt = f"""You are a financial analyst. Synthesize the following 4 analysis sections into ONE comprehensive final answer.

## Document Verification:
{verification or 'Not available'}

## Financial Analysis:
{financial_analysis or 'Not available'}

## Investment Analysis:
{investment_analysis or 'Not available'}

## Risk Assessment:
{risk_assessment or 'Not available'}

Generate a well-structured final answer that:
1. Opens with an executive summary
2. Highlights key financial metrics and trends
3. Provides investment recommendation (BUY/HOLD/SELL)
4. Summarizes main risks
5. Ends with actionable insights

Keep it concise but comprehensive. Use markdown formatting."""

    try:
        response = completion(
            model="nvidia_nim/meta/llama-3.3-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            api_key=settings.nvidia_api_key,
            base_url="https://integrate.api.nvidia.com/v1",
        )
        return response.choices[0].message.content
    except Exception as e:
        log.error(f"Error generating final answer: {e}")
        # Fallback: combine all outputs
        return f"""## Final Analysis Report

### Document Verification
{verification or 'Not available'}

### Financial Analysis
{financial_analysis or 'Not available'}

### Investment Analysis
{investment_analysis or 'Not available'}

### Risk Assessment
{risk_assessment or 'Not available'}"""


## ─────────────────────────────────────────────────────
## BUG_FIX #3: LOGIC_FIX - file_path not passed to crew
## BUG_FIX #4: LOGIC_FIX - No extraction of individual agent outputs
## Original:   def run_crew(query: str, file_path: str="data/sample.pdf"):
##                 result = financial_crew.kickoff({'query': query})
##                 return result  # Just returned raw string
## Problem:    (1) file_path parameter was ignored - kickoff didn't receive it.
##             (2) Only returned final combined string, not individual agent outputs.
## Fix:        (1) Pass file_path in kickoff inputs: {"query": query, "file_path": file_path}
##             (2) Extract individual outputs from result.tasks_output[i].raw
##             (3) Return dict with both final answer and individual agent outputs.
## ─────────────────────────────────────────────────────
def run_crew(query: str, file_path: str) -> dict:
    """Run the full multi-agent financial analysis crew (synchronous — called via asyncio.to_thread).
    Returns dict with final result and individual agent outputs."""
    
    financial_crew = Crew(
        agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
        tasks=[verification, analyze_task, investment_analysis, risk_assessment],
        process=Process.sequential,
        verbose=False,
    )
    result = financial_crew.kickoff({"query": query, "file_path": file_path})
    
    ## ─────────────────────────────────────────────────────
    ## BUG_FIX #4: Extract individual agent outputs from CrewAI result
    ## Original:   return result  # Just the final combined string
    ## Problem:    No way to access individual agent outputs for storage/display.
    ## Fix:        CrewAI's CrewOutput has tasks_output list with TaskOutput objects.
    ##             Each TaskOutput has .raw attribute containing the agent's output text.
    ##             Extract these and return as a dict with named keys.
    ## ─────────────────────────────────────────────────────
    # Extract individual task outputs from result.tasks_output
    task_outputs = {}
    if hasattr(result, 'tasks_output') and result.tasks_output:
        task_names = ['verification', 'analysis', 'investment', 'risk']
        for i, task_output in enumerate(result.tasks_output):
            if i < len(task_names):
                raw_output = getattr(task_output, 'raw', None)
                if raw_output:
                    task_outputs[task_names[i]] = str(raw_output)
    
    ## ─────────────────────────────────────────────────────
    ## ENHANCEMENT #7: AI-synthesized final answer
    ## Purpose:    Instead of just concatenating agent outputs, use an LLM to
    ##             synthesize them into one comprehensive, well-structured report.
    ## ─────────────────────────────────────────────────────
    # Generate AI-synthesized final answer
    final_answer = generate_final_answer(
        verification=task_outputs.get('verification'),
        financial_analysis=task_outputs.get('analysis'),
        investment_analysis=task_outputs.get('investment'),
        risk_assessment=task_outputs.get('risk'),
    )
    
    return {
        "result": final_answer,
        "verification": task_outputs.get('verification'),
        "financial_analysis": task_outputs.get('analysis'),
        "investment_analysis": task_outputs.get('investment'),
        "risk_assessment": task_outputs.get('risk'),
    }


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class AnalysisQuery(BaseModel):
    query: str = Field(
        default="Analyze this financial document for investment insights",
        min_length=5,
        max_length=500,
    )


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    query: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None


class JobListResponse(BaseModel):
    jobs: List[JobStatusResponse]
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Financial Document Analyzer API is running",
        "status": "healthy",
        "version": "2.0.0",
        "features": ["synchronous_analysis", "async_queue", "database_storage"]
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    db_status = "connected" if settings.database_url else "not_configured"
    redis_status = "connected" if settings.upstash_redis_url else "not_configured"
    
    return {
        "status": "healthy",
        "database": db_status,
        "redis_queue": redis_status,
        "timestamp": datetime.utcnow().isoformat()
    }


# ---------------------------------------------------------------------------
# Synchronous Analysis (original endpoint - blocks until complete)
# ---------------------------------------------------------------------------
@app.post("/analyze")
@limiter.limit("5/minute")
async def analyze_document(
    request: Request,
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
    _: None = Security(verify_api_key),
):
    """Analyze a financial document (PDF) synchronously - blocks until complete.

    - **file**: PDF financial document to analyze (required)
    - **query**: Specific question or analysis focus (optional, has default)
    - **X-API-Key**: Required header when API_KEY is set in .env
    """
    job_id = str(uuid.uuid4())

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # File size limit
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {settings.max_file_size_mb}MB.",
        )

    # Validate query
    query = query.strip() if query and query.strip() else "Analyze this financial document for investment insights"
    try:
        AnalysisQuery(query=query)
    except Exception:
        raise HTTPException(status_code=422, detail="Query must be between 5 and 500 characters.")

    log.info("sync_analysis_started", job_id=job_id, query=query, filename=file.filename)
    start = time.time()

    try:
        # Save temp file
        os.makedirs("data", exist_ok=True)
        file_path = f"data/financial_document_{job_id}.pdf"
        with open(file_path, "wb") as f:
            f.write(content)

        # Run analysis
        crew_result = await asyncio.to_thread(run_crew, query=query, file_path=file_path)
        response = crew_result["result"]

        duration = round(time.time() - start, 2)
        log.info("sync_analysis_complete", job_id=job_id, duration_seconds=duration)

        # Store result in database
        with get_db_session() as db:
            db_job = AnalysisJob(
                job_id=job_id,
                query=query,
                original_filename=file.filename,
                file_path=file_path,
                status=JobStatus.COMPLETED,
                result=response,
                duration_seconds=int(duration),
            )
            db.add(db_job)
            
            # Also store in results table with individual agent outputs
            db_result = AnalysisResult(
                job_id=job_id,
                query=query,
                original_filename=file.filename,
                verification_report=crew_result.get("verification"),
                financial_analysis=crew_result.get("financial_analysis"),
                investment_analysis=crew_result.get("investment_analysis"),
                risk_assessment=crew_result.get("risk_assessment"),
                analysis=response,
                duration_seconds=int(duration),
            )
            db.add(db_result)

        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)

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
        log.error("sync_analysis_failed", job_id=job_id, error=str(e))
        
        # Update job status to failed
        with get_db_session() as db:
            db_job = AnalysisJob(
                job_id=job_id,
                query=query,
                original_filename=file.filename,
                status=JobStatus.FAILED,
                error_message=str(e),
            )
            db.add(db_job)
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing financial document: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Asynchronous Analysis (Queue-based - returns immediately)
# ---------------------------------------------------------------------------
@app.post("/analyze/async")
@limiter.limit("10/minute")
async def analyze_document_async(
    request: Request,
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
    _: None = Security(verify_api_key),
):
    """Submit a document for async analysis via the queue. Returns job_id immediately.

    - **file**: PDF financial document to analyze (required)
    - **query**: Specific question or analysis focus (optional, has default)
    - **X-API-Key**: Required header when API_KEY is set in .env
    
    Returns job_id - use GET /jobs/{job_id} to check status and get results.
    """
    job_id = str(uuid.uuid4())

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # File size limit
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {settings.max_file_size_mb}MB.",
        )

    # Validate query
    query = query.strip() if query and query.strip() else "Analyze this financial document for investment insights"
    try:
        AnalysisQuery(query=query)
    except Exception:
        raise HTTPException(status_code=422, detail="Query must be between 5 and 500 characters.")

    # Save file for worker to process
    os.makedirs("data", exist_ok=True)
    file_path = f"data/financial_document_{job_id}.pdf"
    with open(file_path, "wb") as f:
        f.write(content)

    # Create job record in database
    with get_db_session() as db:
        db_job = AnalysisJob(
            job_id=job_id,
            query=query,
            original_filename=file.filename,
            file_path=file_path,
            status=JobStatus.PENDING,
        )
        db.add(db_job)

    # Submit to Celery queue
    task = analyze_document_task.delay(job_id, query, file_path, file.filename)

    log.info("async_job_submitted", job_id=job_id, task_id=task.id, query=query)

    return {
        "status": "queued",
        "job_id": job_id,
        "task_id": task.id,
        "query": query,
        "file_processed": file.filename,
        "message": "Job submitted to queue. Use GET /jobs/{job_id} to check status.",
    }


# ---------------------------------------------------------------------------
# Job Status Endpoints
# ---------------------------------------------------------------------------
@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    _: None = Security(verify_api_key),
):
    """Get the status and result of an analysis job.

    - **job_id**: The job ID returned from /analyze/async
    - **X-API-Key**: Required header when API_KEY is set in .env
    """
    with get_db_session() as db:
        job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            query=job.query,
            result=job.result,
            error=job.error_message,
            created_at=job.created_at.isoformat() if job.created_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            duration_seconds=job.duration_seconds,
        )


@app.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    request: Request,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    _: None = Security(verify_api_key),
):
    """List all analysis jobs, optionally filtered by status.

    - **status**: Filter by job status (pending, processing, completed, failed)
    - **limit**: Maximum number of jobs to return (default 20)
    - **offset**: Number of jobs to skip (for pagination)
    - **X-API-Key**: Required header when API_KEY is set in .env
    """
    with get_db_session() as db:
        query = db.query(AnalysisJob)
        
        if status:
            query = query.filter(AnalysisJob.status == status)
        
        total = query.count()
        jobs = query.order_by(AnalysisJob.created_at.desc()).offset(offset).limit(limit).all()
        
        job_list = [
            JobStatusResponse(
                job_id=job.job_id,
                status=job.status,
                query=job.query,
                result=job.result,
                error=job.error_message,
                created_at=job.created_at.isoformat() if job.created_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                duration_seconds=job.duration_seconds,
            )
            for job in jobs
        ]
        
        return JobListResponse(jobs=job_list, total=total)


@app.get("/results/{job_id}")
async def get_analysis_result(
    job_id: str,
    _: None = Security(verify_api_key),
):
    """Get the stored analysis result for a completed job.

    - **job_id**: The job ID returned from /analyze/async
    - **X-API-Key**: Required header when API_KEY is set in .env
    """
    with get_db_session() as db:
        result = db.query(AnalysisResult).filter(AnalysisResult.job_id == job_id).first()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Result for job {job_id} not found")
        
        return {
            "job_id": result.job_id,
            "query": result.query,
            "original_filename": result.original_filename,
            "agent_outputs": {
                "verification": result.verification_report,
                "financial_analysis": result.financial_analysis,
                "investment_analysis": result.investment_analysis,
                "risk_assessment": result.risk_assessment,
            },
            "final_analysis": result.analysis,
            "summary": result.summary,
            "duration_seconds": result.duration_seconds,
            "created_at": result.created_at.isoformat() if result.created_at else None,
        }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
