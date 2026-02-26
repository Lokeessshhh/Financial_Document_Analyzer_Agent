"""
Celery Worker Configuration for async job processing.
Uses Upstash Redis as the broker and result backend.
"""
import time
import logging
from celery import Celery

# Load environment variables first
from dotenv import load_dotenv
load_dotenv(override=True)

from config import settings
from database import get_db_session, AnalysisJob, JobStatus, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery Configuration
# ---------------------------------------------------------------------------
celery_app = Celery(
    "financial_analyzer",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery settings optimized for Upstash Redis
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Only fetch one task at a time
    worker_concurrency=2,  # Number of concurrent workers
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Broker connection settings
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=5,
    
    # Task routing
    task_routes={
        "worker.analyze_document_task": {"queue": "analysis"},
    },
)


# ---------------------------------------------------------------------------
# Initialize Database on Worker Startup
# ---------------------------------------------------------------------------
@celery_app.on_after_configure.connect
def init_worker_db(sender, **kwargs):
    """Initialize database tables when worker starts."""
    logger.info("Initializing database connection...")
    init_db()
    logger.info("Database initialized successfully")


# ---------------------------------------------------------------------------
# Analysis Task
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, name="analyze_document_task")
def analyze_document_task(self, job_id: str, query: str, file_path: str, original_filename: str):
    """
    Celery task to run the financial document analysis.
    
    Args:
        job_id: Unique job identifier
        query: User's analysis query
        file_path: Path to the uploaded PDF file
        original_filename: Original filename from upload
    """
    from crewai import Crew, Process
    from agents import financial_analyst, verifier, investment_advisor, risk_assessor
    from task import (
        verification,
        analyze_financial_document as analyze_task,
        investment_analysis,
        risk_assessment,
    )
    
    logger.info(f"Starting analysis for job {job_id}")
    start_time = time.time()
    
    # Update job status to processing
    with get_db_session() as db:
        job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        if job:
            job.status = JobStatus.PROCESSING
            db.add(job)
    
    try:
        # Run the CrewAI analysis
        financial_crew = Crew(
            agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
            tasks=[verification, analyze_task, investment_analysis, risk_assessment],
            process=Process.sequential,
            verbose=False,
        )
        
        result = financial_crew.kickoff({"query": query, "file_path": file_path})
        result_str = str(result)
        
        duration = int(time.time() - start_time)
        logger.info(f"Analysis completed for job {job_id} in {duration}s")
        
        # Update job status to completed
        with get_db_session() as db:
            job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
            if job:
                job.status = JobStatus.COMPLETED
                job.result = result_str
                job.duration_seconds = duration
                job.completed_at = time.strftime("%Y-%m-%d %H:%M:%S")
                db.add(job)
                
                # Also store in results table
                from database import AnalysisResult
                db_result = AnalysisResult(
                    job_id=job_id,
                    query=query,
                    original_filename=original_filename,
                    analysis=result_str,
                    duration_seconds=duration,
                )
                db.add(db_result)
        
        # Clean up temp file
        import os
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
        
        return {"status": "success", "job_id": job_id, "duration": duration}
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Analysis failed for job {job_id}: {error_msg}")
        
        # Update job status to failed
        with get_db_session() as db:
            job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = error_msg
                job.completed_at = time.strftime("%Y-%m-%d %H:%M:%S")
                db.add(job)
        
        # Clean up temp file on failure too
        import os
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        
        raise


# ---------------------------------------------------------------------------
# Worker Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting Celery worker...")
    celery_app.worker_main(["worker", "--loglevel=info"])
