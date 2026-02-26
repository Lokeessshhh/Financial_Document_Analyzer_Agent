# Financial Document Analyzer

An AI-powered financial document analysis system built with [CrewAI](https://docs.crewai.com/) and [FastAPI](https://fastapi.tiangolo.com/). Upload any financial PDF (earnings reports, 10-K/10-Q filings, investor updates) and receive a comprehensive multi-agent analysis covering document verification, financial analysis, investment recommendations, and risk assessment.

**Version 2.0** now supports:
- 🚀 **Queue-based async processing** with Celery + Upstash Redis
- 🗄️ **Persistent storage** with Neon PostgreSQL
- 📊 **Job tracking** and result retrieval

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Setup & Installation](#setup--installation)
- [API Documentation](#api-documentation)
- [Deployment Guide](#deployment-guide)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)

---

## Features

- 📄 **PDF Upload** — Upload any financial PDF via REST API
- 🤖 **Multi-Agent Analysis** — Four specialized CrewAI agents work sequentially:
  - **Document Verifier** — Confirms the document is a genuine financial report
  - **Financial Analyst** — Extracts key metrics, trends, and insights
  - **Investment Advisor** — Provides evidence-based BUY/HOLD/SELL recommendations
  - **Risk Assessor** — Evaluates market, credit, operational, and macro risks
- 🔍 **Web Search** — Agents can search the internet for current market context
- ⚡ **Async FastAPI** — Non-blocking API with thread-pool execution
- 🚀 **Queue Processing** — Handle concurrent requests with Celery + Redis
- 🗄️ **Database Storage** — Store analysis results and job history in PostgreSQL

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Request                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ POST /analyze│  │POST /analyze │  │ GET /jobs/{job_id}   │   │
│  │  (sync)      │  │  /async      │  │ GET /jobs            │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘   │
└─────────┼─────────────────┼─────────────────────────────────────┘
          │                 │
          │                 ▼
          │    ┌────────────────────────┐
          │    │   Upstash Redis Queue  │
          │    └────────────┬───────────┘
          │                 │
          │                 ▼
          │    ┌────────────────────────┐
          │    │   Celery Worker       │
          │    │   (Background Tasks)  │
          │    └────────────┬───────────┘
          │                 │
          ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CrewAI Agents                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Verifier │→ │ Analyst  │→ │ Advisor  │→ │ Risk     │         │
│  │          │  │          │  │          │  │ Assessor │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Neon PostgreSQL Database                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ analysis_jobs│  │analysis_results│ │ users       │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- NVIDIA NIM API key (or OpenAI API key)
- Upstash Redis account (for queue processing)
- Neon PostgreSQL account (for database)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd financial-document-analyzer-debug
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### 5. Run the server

**Development (API only):**
```bash
python main.py
```

**Development (with queue worker):**
```bash
# Terminal 1 - API Server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Celery Worker
python -m worker
```

---

## API Documentation

### `GET /`
Health check endpoint.

### `GET /health`
Detailed health check with database and Redis status.

### `POST /analyze`
**Synchronous analysis** - blocks until complete.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file (PDF) | ✅ Yes | Financial PDF to analyze |
| `query` | string | ❌ No | Analysis focus (default provided) |

**Response:**
```json
{
  "status": "success",
  "job_id": "uuid",
  "query": "Analyze this document...",
  "analysis": "Full analysis text...",
  "duration_seconds": 45
}
```

### `POST /analyze/async`
**Asynchronous analysis** - returns immediately with job_id.

**Response:**
```json
{
  "status": "queued",
  "job_id": "uuid",
  "task_id": "celery-task-id",
  "message": "Job submitted to queue. Use GET /jobs/{job_id} to check status."
}
```

### `GET /jobs/{job_id}`
Get job status and result.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "query": "...",
  "result": "Full analysis...",
  "duration_seconds": 45,
  "created_at": "2024-01-15T10:30:00",
  "completed_at": "2024-01-15T10:31:00"
}
```

### `GET /jobs`
List all jobs with optional filtering.

| Query Param | Type | Description |
|-------------|------|-------------|
| `status` | string | Filter by status (pending, processing, completed, failed) |
| `limit` | int | Max results (default 20) |
| `offset` | int | Pagination offset |

### `GET /results/{job_id}`
Get stored analysis result for a completed job.

---

## Deployment Guide

### Step 1: Get API Keys

#### NVIDIA NIM API Key (LLM Provider)
1. Go to https://build.nvidia.com/
2. Sign in or create an account
3. Navigate to **API Keys** section
4. Click **Generate Key**
5. Copy the key to `NVIDIA_API_KEY` in your `.env`

#### Upstash Redis (Queue Broker)
1. Go to https://upstash.com/
2. Create a free account
3. Click **Create Database**
4. Choose a name (e.g., `financial-analyzer`)
5. Select a region close to your deployment
6. After creation, copy the **Connection String**
7. Format: `redis://default:PASSWORD@HOST.upstash.io:6379`
8. Add to `UPSTASH_REDIS_URL` in your `.env`

#### Neon PostgreSQL (Database)
1. Go to https://neon.tech/
2. Create a free account
3. Click **Create a Project**
4. Name it `financial-analyzer`
5. Select a region
6. After creation, copy the **Connection String**
7. Format: `postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require`
8. Add to `DATABASE_URL` in your `.env`

### Step 2: Database Tables

The application automatically creates tables on startup. The following tables are created:

```sql
-- Users table (for API authentication)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    api_key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_active_at TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Analysis jobs table (job tracking)
CREATE TABLE analysis_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(36) UNIQUE NOT NULL,
    user_id INTEGER,
    query TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    status VARCHAR(20) DEFAULT 'pending',
    result TEXT,
    error_message TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Analysis results table (persistent storage)
CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(36) UNIQUE NOT NULL,
    query TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    analysis TEXT NOT NULL,
    summary TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Step 3: Deploy to Render

#### Option A: Using render.yaml (Blueprint)

1. Push your code to GitHub/GitLab
2. Go to https://dashboard.render.com/
3. Click **New** → **Blueprint**
4. Connect your repository
5. Render will detect `render.yaml` and create:
   - Web service (FastAPI)
   - Worker service (Celery)
   - Redis instance
   - PostgreSQL database
6. Set `NVIDIA_API_KEY` manually in the dashboard
7. Deploy!

#### Option B: Manual Setup

1. **Create Redis:**
   - New → Redis
   - Name: `financial-analyzer-redis`
   - Plan: Free

2. **Create Database:**
   - New → PostgreSQL (or use external Neon)
   - Name: `financial-analyzer-db`

3. **Create Web Service:**
   - New → Web Service
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables from `.env`

4. **Create Worker:**
   - New → Background Worker
   - Build: `pip install -r requirements.txt`
   - Start: `python -m worker`
   - Add same environment variables

### Step 4: Verify Deployment

1. Check health: `GET https://your-app.onrender.com/health`
2. Test sync analysis: `POST /analyze`
3. Test async analysis: `POST /analyze/async` → `GET /jobs/{job_id}`

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NVIDIA_API_KEY` | ✅ Yes | NVIDIA NIM API key for LLM |
| `OPENAI_API_KEY` | ❌ Alt | OpenAI API key (alternative to NVIDIA) |
| `API_KEY` | ❌ Rec | API key for authentication |
| `UPSTASH_REDIS_URL` | ✅ Yes | Redis connection string for Celery |
| `DATABASE_URL` | ✅ Yes | PostgreSQL connection string |
| `MAX_FILE_SIZE_MB` | ❌ No | Max upload size (default: 10) |
| `DEBUG` | ❌ No | Enable debug mode (default: false) |
| `SENTRY_DSN` | ❌ No | Sentry error tracking |

---

## Project Structure

```
financial-document-analyzer-debug/
├── main.py              # FastAPI application
├── config.py            # Centralized settings (Pydantic)
├── database.py          # SQLAlchemy models & connection
├── worker.py            # Celery worker configuration
├── agents.py            # CrewAI agent definitions
├── task.py              # CrewAI task definitions
├── tools.py             # Custom @tool functions
├── requirements.txt     # Python dependencies
├── Procfile             # Process definitions (Render)
├── render.yaml          # Render Blueprint
├── .env.example         # Environment template
├── data/                # Uploaded PDFs (temporary)
└── outputs/             # Analysis outputs
```

---

## Notes

- Analysis takes **30–120 seconds** depending on document length
- The system uses **sequential** CrewAI process
- Async processing recommended for production workloads
- Free tier limits: Upstash (10K commands/day), Neon (0.5GB storage)
- This tool is for **informational purposes only**
