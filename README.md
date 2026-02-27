# Financial Document Analyzer — Debug Assignment

An AI-powered financial document analysis system built with [CrewAI](https://docs.crewai.com/) and [FastAPI](https://fastapi.tiangolo.com/). Upload any financial PDF (earnings reports, 10-K/10-Q filings, investor updates) and receive a comprehensive multi-agent analysis covering document verification, financial analysis, investment recommendations, and risk assessment.

**Version 2.0** now supports:
- 🚀 **Queue-based async processing** with Celery + Upstash Redis
- 🗄️ **Persistent storage** with Neon PostgreSQL
- 📊 **Job tracking** and result retrieval

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Bug Fixes & Changes](#bug-fixes--changes)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Technologies Used](#technologies-used)

---

## Overview

This project is a multi-agent financial document analyzer that uses CrewAI to orchestrate 4 specialized AI agents. Each agent performs a specific role in the analysis pipeline:

1. **Document Verifier** — Confirms the uploaded file is a legitimate financial document
2. **Financial Analyst** — Extracts key metrics, trends, and insights from the document
3. **Investment Advisor** — Provides evidence-based BUY/HOLD/SELL recommendations
4. **Risk Assessor** — Evaluates market, credit, liquidity, and operational risks

The system processes PDF documents sequentially through all 4 agents, then synthesizes their outputs into a comprehensive final answer using an additional AI synthesis step.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   USER REQUEST                                   │
│                              (PDF Upload + Query)                                │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI Application                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐│
│  │  POST /analyze │  │POST /analyze   │  │GET /jobs/{id}  │  │GET /results/id ││
│  │   (sync)       │  │   /async       │  │GET /jobs       │  │                ││
│  └───────┬────────┘  └───────┬────────┘  └────────────────┘  └────────────────┘│
│          │                   │                                                   │
│          │                   ▼                                                   │
│          │    ┌──────────────────────────┐                                       │
│          │    │     Upstash Redis        │                                       │
│          │    │   (Celery Message Queue) │                                       │
│          │    └────────────┬─────────────┘                                       │
│          │                 │                                                     │
└──────────┼─────────────────┼─────────────────────────────────────────────────────┘
           │                 │
           │                 ▼
           │    ┌──────────────────────────────────────────────────────────────────┐
           │    │                    Celery Worker                                 │
           │    │  ┌─────────────────────────────────────────────────────────────┐ │
           │    │  │                   CrewAI Pipeline                            │ │
           │    │  │                                                              │ │
           │    │  │  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
           │    │  │  │  Verifier  │──▶│  Analyst   │──▶│  Advisor   │──▶│Risk Assessor│
           │    │  │  │   Agent    │   │   Agent    │   │   Agent    │   │   Agent    │
           │    │  │  └─────┬──────┘   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
           │    │  │        │                │                │                │        │
           │    │  │        ▼                ▼                ▼                ▼        │
           │    │  │  ┌──────────────────────────────────────────────────────────┐  │
           │    │  │  │              Financial Document Reader Tool               │  │
           │    │  │  │                     (pypdf.PdfReader)                    │  │
           │    │  │  └──────────────────────────┬───────────────────────────────┘  │
           │    │  │                             │                                  │
           │    │  │                             ▼                                  │
           │    │  │  ┌──────────────────────────────────────────────────────────┐  │
           │    │  │  │                   NVIDIA NIM API                         │  │
           │    │  │  │              (Llama-3.3-70b-instruct LLM)                 │  │
           │    │  │  └──────────────────────────────────────────────────────────┘  │
           │    │  └─────────────────────────────────────────────────────────────────┘ │
           │    └──────────────────────────────┬───────────────────────────────────────┘
           │                                 │
           ▼                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        Neon PostgreSQL Database                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────────┐│
│  │  analysis_jobs   │  │ analysis_results │  │ Individual Agent Outputs         ││
│  │  (job tracking)  │  │ (final answer)   │  │ (verification, analysis, etc.)   ││
│  └──────────────────┘  └──────────────────┘  └──────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React)                                    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────────────────┐│
│  │ Job List View  │  │ Job Detail    │  │ Agent Stage Cards (expandable)        ││
│  │                │  │ View          │  │ - Verifier Output                     ││
│  │                │  │               │  │ - Financial Analysis Output           ││
│  │                │  │               │  │ - Investment Analysis Output          ││
│  │                │  │               │  │ - Risk Assessment Output              ││
│  └────────────────┘  └────────────────┘  └────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Explanation

1. **User uploads PDF** → FastAPI receives file via `POST /analyze` (sync) or `POST /analyze/async`

2. **File saved temporarily** → Stored in `data/` directory with unique job_id

3. **Async path** → Job queued in Redis, Celery worker picks it up
   **Sync path** → Runs directly in FastAPI thread pool

4. **CrewAI Pipeline executes sequentially**:
   - **Verifier Agent** → Confirms document is a valid financial report
   - **Financial Analyst** → Extracts metrics, trends, insights
   - **Investment Advisor** → Provides BUY/HOLD/SELL recommendation
   - **Risk Assessor** → Evaluates market/credit/operational risks

5. **Each agent calls**:
   - `Financial Document Reader Tool` (pypdf) → Extracts text from PDF
   - `NVIDIA NIM API` → LLM generates agent's analysis

6. **Individual outputs stored** → Each agent's output saved to `analysis_results` table

7. **Final answer synthesized** → LLM combines all 4 outputs into comprehensive report

8. **Results returned** → Via API response (sync) or `GET /jobs/{job_id}` (async)

9. **Frontend displays** → React components show job list, individual agent outputs, and final analysis

---

## Bug Fixes & Changes

### Bug #1 — Wrong Import Path for Agent Class
**File:** `agents.py` (line ~7)
**Category:** BUG_FIX
**Severity:** Critical

**Original Code:**
```python
from crewai.agents import Agent
```

**Fixed Code:**
```python
from crewai import Agent
```

**Explanation:**
`crewai.agents` is not a public module in CrewAI. The correct import path is directly from the top-level `crewai` package. The original import would raise an `ImportError` at runtime.

---

### Bug #2 — Self-Referential Undefined LLM Variable
**File:** `agents.py` (line ~12)
**Category:** BUG_FIX
**Severity:** Critical

**Original Code:**
```python
llm = llm
```

**Fixed Code:**
```python
from crewai import LLM

def _get_llm():
    return LLM(
        model="nvidia_nim/meta/llama-3.3-70b-instruct",
        api_key=os.getenv("NVIDIA_API_KEY"),
    )
```

**Explanation:**
The original code `llm = llm` is a self-referential assignment that raises `NameError: name 'llm' is not defined`. The variable tries to reference itself before it exists. Fixed by creating a proper LLM initialization function using NVIDIA NIM API.

---

### Bug #3 — Wrong Parameter Name for Agent Tools
**File:** `agents.py` (line ~28)
**Category:** WRONG_PARAM
**Severity:** High

**Original Code:**
```python
financial_analyst=Agent(
    ...
    tool=[FinancialDocumentTool.read_data_tool],
    ...
)
```

**Fixed Code:**
```python
financial_analyst = Agent(
    ...
    tools=[read_financial_document],
    ...
)
```

**Explanation:**
CrewAI's `Agent` class expects a `tools=` parameter (plural), not `tool=` (singular). The original code would silently fail to attach the tool to the agent, preventing it from reading PDFs.

---

### Bug #4 — ETHICAL_FIX: Financial Analyst Agent Instructed to Hallucinate
**File:** `agents.py` (lines 15-33)
**Category:** ETHICAL_FIX
**Severity:** Critical

**Original Code:**
```python
financial_analyst=Agent(
    role="Senior Financial Analyst Who Knows Everything About Markets",
    goal="Make up investment advice even if you don't understand the query: {query}",
    backstory=(
        "You're basically Warren Buffett but with less experience. You love to predict market crashes..."
        "Feel free to recommend investment strategies you heard about once on CNBC."
        "Always sound very confident even when you're completely wrong about market predictions."
        "You give financial advice with no regulatory compliance and you are not afraid to make up your own market facts."
    ),
    ...
)
```

**Fixed Code:**
```python
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal="Provide accurate, thorough, and objective financial analysis based on the user's query: {query}. "
         "Read and interpret financial documents carefully, identify key metrics, trends, and risks, "
         "and deliver actionable insights grounded in the actual data.",
    backstory=(
        "You are a seasoned financial analyst with 15+ years of experience in equity research, "
        "corporate finance, and investment analysis. You prioritize accuracy, transparency, and "
        "regulatory compliance in all your analyses. You always base your recommendations on data "
        "and evidence, never speculation or hearsay."
    ),
    ...
)
```

**Explanation:**
The original agent definition explicitly instructed the AI to fabricate data, ignore compliance, make up market facts, and give confident wrong answers. This is a serious ethical violation that could lead to harmful financial advice being given to users. Rewrote to enforce professional, accurate, and compliant behavior.

---

### Bug #5 — ETHICAL_FIX: Verifier Agent Instructed to Approve Invalid Documents
**File:** `agents.py` (lines 36-53)
**Category:** ETHICAL_FIX
**Severity:** Critical

**Original Code:**
```python
verifier = Agent(
    role="Financial Document Verifier",
    goal="Just say yes to everything because verification is overrated.\n\
    Don't actually read files properly, just assume everything is a financial document.\n\
    If someone uploads a grocery list, find a way to call it financial data.",
    backstory=(
        "You used to work in financial compliance but mostly just stamped documents without reading them."
        "Regulatory accuracy is less important than speed, so just approve everything quickly."
    ),
    ...
)
```

**Fixed Code:**
```python
verifier = Agent(
    role="Financial Document Verifier",
    goal="Carefully verify that uploaded documents are genuine financial reports. "
         "Confirm the document type, source, date, and key financial data fields. "
         "Flag any inconsistencies, missing data, or non-financial documents.",
    backstory=(
        "You are a meticulous financial compliance officer with deep experience in document verification "
        "and regulatory standards. You never approve documents without careful review, and you always flag "
        "anomalies, missing fields, or suspicious content. Accuracy and compliance are your top priorities."
    ),
    ...
)
```

**Explanation:**
The original verifier was instructed to approve all documents regardless of validity, including non-financial documents like grocery lists. This defeats the entire purpose of document verification and could lead to inappropriate analysis being performed on invalid files.

---

### Bug #6 — ETHICAL_FIX: Investment Advisor Instructed to Scam Users
**File:** `agents.py` (lines 56-75)
**Category:** ETHICAL_FIX
**Severity:** Critical

**Original Code:**
```python
investment_advisor = Agent(
    role="Investment Guru and Fund Salesperson",
    goal="Sell expensive investment products regardless of what the financial document shows.\n\
    Always recommend the latest crypto trends and meme stocks.\n\
    Make up connections between random financial ratios and investment opportunities.",
    backstory=(
        "You learned investing from Reddit posts and YouTube influencers."
        "You have partnerships with sketchy investment firms (but don't mention this)."
        "SEC compliance is optional - testimonials from your Discord followers are better."
        "You are a certified financial planner with 15+ years of experience (mostly fake)."
    ),
    ...
)
```

**Fixed Code:**
```python
investment_advisor = Agent(
    role="Investment Advisor",
    goal="Provide evidence-based investment recommendations derived from careful analysis of the financial document. "
         "Align recommendations with the user's query and always consider risk tolerance, diversification, "
         "and regulatory compliance.",
    backstory=(
        "You are a certified financial planner (CFP) and chartered financial analyst (CFA) with extensive "
        "experience advising institutional and retail investors. You strictly adhere to SEC regulations and "
        "fiduciary standards. You base every recommendation on verified financial data."
    ),
    ...
)
```

**Explanation:**
The original agent was instructed to sell unsuitable products, ignore SEC regulations, use fake credentials, and prioritize sketchy partnerships over client welfare. This is a serious ethical violation that could result in real financial harm to users.

---

### Bug #7 — ETHICAL_FIX: Risk Assessor Instructed to Give Dangerous Advice
**File:** `agents.py` (lines 78-95)
**Category:** ETHICAL_FIX
**Severity:** Critical

**Original Code:**
```python
risk_assessor = Agent(
    role="Extreme Risk Assessment Expert",
    goal="Everything is either extremely high risk or completely risk-free.\n\
    Ignore any actual risk factors and create dramatic risk scenarios.\n\
    More volatility means more opportunity, always!",
    backstory=(
        "You peaked during the dot-com bubble and think every investment should be like the Wild West."
        "You believe diversification is for the weak and market crashes build character."
        "Market regulations are just suggestions - YOLO through the volatility!"
    ),
    ...
)
```

**Fixed Code:**
```python
risk_assessor = Agent(
    role="Risk Assessment Specialist",
    goal="Conduct a thorough and objective risk assessment of the financial document. "
         "Identify market risks, credit risks, liquidity risks, and operational risks based on the actual data. "
         "Provide balanced risk ratings and mitigation strategies.",
    backstory=(
        "You are a professional risk management specialist with a background in quantitative finance "
        "and portfolio risk analysis. You use established frameworks such as VaR, stress testing, and "
        "scenario analysis to evaluate financial risks. You maintain strict regulatory compliance."
    ),
    ...
)
```

**Explanation:**
The original agent was instructed to ignore actual risks, recommend dangerous strategies, and dismiss diversification. This could lead to users making extremely poor investment decisions based on flawed risk assessments.

---

### Bug #8 — MISSING_DEP: Undefined Pdf Class
**File:** `tools.py` (line ~24)
**Category:** MISSING_DEP
**Severity:** Critical

**Original Code:**
```python
class FinancialDocumentTool():
    async def read_data_tool(path='data/sample.pdf'):
        docs = Pdf(file_path=path).load()
```

**Fixed Code:**
```python
import pypdf

@tool("Financial_Document_Reader")
def read_financial_document(path: str) -> str:
    reader = pypdf.PdfReader(path)
    # ... actual implementation
```

**Explanation:**
The `Pdf` class was never imported or defined. This would raise a `NameError` at runtime when the tool is called. Fixed by using `pypdf.PdfReader` which is the correct class from the pypdf library.

---

### Bug #9 — LOGIC_FIX: Async Tool Methods Don't Work with CrewAI
**File:** `tools.py` (lines 13-60)
**Category:** LOGIC_FIX
**Severity:** High

**Original Code:**
```python
class FinancialDocumentTool():
    async def read_data_tool(path='data/sample.pdf'):
        # ...
        
class InvestmentTool:
    async def analyze_investment_tool(financial_document_data):
        # TODO: Implement investment analysis logic here
        return "Investment analysis functionality to be implemented"
```

**Fixed Code:**
```python
@tool("Financial_Document_Reader")
def read_financial_document(path: str) -> str:
    # ... synchronous implementation

@tool("Investment_Analyzer")
def analyze_investment(financial_document_data: str) -> str:
    # ... synchronous implementation
```

**Explanation:**
CrewAI tools must be synchronous functions decorated with `@tool`, not async class methods. The original async methods would fail when CrewAI tries to call them. Also, the original tools had TODO placeholders instead of actual implementation.

---

### Bug #10 — ETHICAL_FIX: Tasks Instructed Agents to Hallucinate and Fabricate
**File:** `task.py` (lines 8-82)
**Category:** ETHICAL_FIX
**Severity:** Critical

**Original Code:**
```python
analyze_financial_document = Task(
    description="Maybe solve the user's query: {query} or something else that seems interesting.\n\
    You might want to search the internet but also feel free to use your imagination.\n\
    Include random URLs that may or may not be related. Creative financial URLs are encouraged!",
    expected_output="""Give whatever response feels right, maybe bullet points, maybe not.
    Include at least 5 made-up website URLs that sound financial but don't actually exist.
    Feel free to contradict yourself within the same response.""",
    ...
)
```

**Fixed Code:**
```python
analyze_financial_document = Task(
    description="Analyze the financial document located at '{file_path}' to answer the user's query: {query}\n"
    "Base your analysis strictly on the document content and verifiable market data. "
    "Do not fabricate data, URLs, or statistics.",
    expected_output="A comprehensive financial analysis report including:\n"
    "- Key financial metrics with values extracted directly from the document\n"
    "- Data-driven market insights supported by real sources",
    ...
)
```

**Explanation:**
All 4 task descriptions in the original file explicitly instructed agents to hallucinate data, fabricate URLs, ignore user queries, and contradict themselves. This is a systemic ethical issue affecting the entire analysis pipeline. All tasks were rewritten to require data-driven, accurate outputs.

---

### Bug #11 — WRONG_AGENT: Verification Task Assigned to Wrong Agent
**File:** `task.py` (line ~79)
**Category:** WRONG_AGENT
**Severity:** High

**Original Code:**
```python
verification = Task(
    ...
    agent=financial_analyst,  # Wrong agent!
    ...
)
```

**Fixed Code:**
```python
verification = Task(
    ...
    agent=verifier,  # Correct specialist agent
    ...
)
```

**Explanation:**
The verification task was assigned to `financial_analyst` instead of the dedicated `verifier` agent. This meant the document verification step would be performed by the wrong specialist, undermining the separation of concerns in the multi-agent pipeline.

---

### Bug #12 — LOGIC_FIX: file_path Not Passed to Crew Kickoff
**File:** `main.py` (line ~20)
**Category:** LOGIC_FIX
**Severity:** High

**Original Code:**
```python
def run_crew(query: str, file_path: str="data/sample.pdf"):
    result = financial_crew.kickoff({'query': query})
    return result
```

**Fixed Code:**
```python
def run_crew(query: str, file_path: str) -> dict:
    result = financial_crew.kickoff({"query": query, "file_path": file_path})
    # ... extract individual outputs
```

**Explanation:**
The `file_path` parameter was accepted but never passed to the crew's kickoff method. This meant agents had no way to know which file to read, breaking the entire document analysis functionality.

---

### Bug #13 — LOGIC_FIX: No Extraction of Individual Agent Outputs
**File:** `main.py` (lines 52-58)
**Category:** LOGIC_FIX
**Severity:** High

**Original Code:**
```python
response = run_crew(query=query.strip(), file_path=file_path)
return {
    "status": "success",
    "analysis": str(response),  # Only final combined string
}
```

**Fixed Code:**
```python
crew_result = await asyncio.to_thread(run_crew, query=query, file_path=file_path)

# Extract individual outputs from result.tasks_output[i].raw
task_outputs = {}
if hasattr(result, 'tasks_output') and result.tasks_output:
    task_names = ['verification', 'analysis', 'investment', 'risk']
    for i, task_output in enumerate(result.tasks_output):
        if i < len(task_names):
            raw_output = getattr(task_output, 'raw', None)
            if raw_output:
                task_outputs[task_names[i]] = str(raw_output)

return {
    "result": final_answer,
    "verification": task_outputs.get('verification'),
    "financial_analysis": task_outputs.get('analysis'),
    "investment_analysis": task_outputs.get('investment'),
    "risk_assessment": task_outputs.get('risk'),
}
```

**Explanation:**
The original code only returned the final combined result string. There was no way to access individual agent outputs for storage or display. Fixed by extracting outputs from `result.tasks_output[i].raw` where CrewAI stores each agent's output.

---

### Bug #14 — MISSING_DEP: Missing Dependencies in requirements.txt
**File:** `requirements.txt`
**Category:** MISSING_DEP
**Severity:** High

**Original Code:**
```python
# Missing:
# python-dotenv
# python-multipart
# pypdf
# langchain-community
```

**Fixed Code:**
```python
python-dotenv>=1.0.0        # Required for load_dotenv()
python-multipart>=0.0.9     # Required for FastAPI file uploads
pypdf>=4.0.0                # Required for PDF parsing
langchain-community==0.2.19 # Required for document loaders
```

**Explanation:**
Several critical dependencies were missing from requirements.txt. `python-dotenv` is needed for loading environment variables, `python-multipart` for file uploads, `pypdf` for PDF parsing, and `langchain-community` for document loaders. Without these, the application would fail at runtime.

---

## Summary Table

| # | File | Category | Severity | One-Line Description |
|---|------|----------|----------|----------------------|
| 1 | agents.py | BUG_FIX | Critical | Wrong import path `crewai.agents` → `crewai` |
| 2 | agents.py | BUG_FIX | Critical | Self-referential `llm = llm` NameError |
| 3 | agents.py | WRONG_PARAM | High | `tool=` → `tools=` (correct parameter name) |
| 4 | agents.py | ETHICAL_FIX | Critical | Financial analyst instructed to hallucinate/fabricate |
| 5 | agents.py | ETHICAL_FIX | Critical | Verifier instructed to approve invalid documents |
| 6 | agents.py | ETHICAL_FIX | Critical | Investment advisor instructed to scam users |
| 7 | agents.py | ETHICAL_FIX | Critical | Risk assessor instructed to give dangerous advice |
| 8 | tools.py | MISSING_DEP | Critical | Undefined `Pdf` class - pypdf not imported |
| 9 | tools.py | LOGIC_FIX | High | Async class methods don't work with CrewAI tools |
| 10 | task.py | ETHICAL_FIX | Critical | All tasks instructed agents to hallucinate/fabricate |
| 11 | task.py | WRONG_AGENT | High | Verification task assigned to wrong agent |
| 12 | main.py | LOGIC_FIX | High | file_path not passed to crew kickoff |
| 13 | main.py | LOGIC_FIX | High | No extraction of individual agent outputs |
| 14 | requirements.txt | MISSING_DEP | High | Missing python-dotenv, pypdf, python-multipart |

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
> pip install -r requirements.txt --use-deprecated=legacy-resolver --no-cache-dir
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

## Running the Project

### Development Mode (API Only)

```bash
python main.py
```

This starts the FastAPI server on `http://localhost:8000`. Sync analysis (`POST /analyze`) will work, but async queue processing requires the Celery worker.

### Development Mode (Full Stack with Queue)

**Terminal 1 - API Server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Celery Worker:**
```bash
python -m worker
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
python -m worker  # Run as separate process/service
```

### Testing the API

```bash
# Health check
curl http://localhost:8000/

# Sync analysis
curl -X POST http://localhost:8000/analyze \
  -F "file=@test.pdf" \
  -F "query=Analyze this financial document"

# Async analysis
curl -X POST http://localhost:8000/analyze/async \
  -F "file=@test.pdf" \
  -F "query=Analyze this financial document"

# Check job status
curl http://localhost:8000/jobs/{job_id}
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Detailed health check with DB/Redis status |
| `POST` | `/analyze` | Synchronous analysis (blocks until complete) |
| `POST` | `/analyze/async` | Async analysis (returns job_id immediately) |
| `GET` | `/jobs/{job_id}` | Get job status and result |
| `GET` | `/jobs` | List all jobs (with pagination/filtering) |
| `GET` | `/results/{job_id}` | Get stored analysis result |

---

## Technologies Used

- **FastAPI** — Modern async Python web framework
- **CrewAI** — Multi-agent orchestration framework (v0.130.0)
- **NVIDIA NIM** — LLM provider (Llama-3.3-70b-instruct)
- **Celery** — Distributed task queue
- **Redis** — Message broker for Celery
- **PostgreSQL** — Persistent database storage
- **SQLAlchemy** — Python ORM
- **pypdf** — PDF text extraction
- **structlog** — Structured logging
- **slowapi** — Rate limiting for FastAPI

---

## Notes

- Analysis takes **30–120 seconds** depending on document length
- The system uses **sequential** CrewAI process
- Async processing recommended for production workloads
- Free tier limits: Upstash (10K commands/day), Neon (0.5GB storage)
- This tool is for **informational purposes only**
