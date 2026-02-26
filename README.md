# Financial Document Analyzer

An AI-powered financial document analysis system built with [CrewAI](https://docs.crewai.com/) and [FastAPI](https://fastapi.tiangolo.com/). Upload any financial PDF (earnings reports, 10-K/10-Q filings, investor updates) and receive a comprehensive multi-agent analysis covering document verification, financial analysis, investment recommendations, and risk assessment.

---

## Table of Contents

- [Bugs Found & Fixes](#bugs-found--fixes)
- [Features](#features)
- [Architecture](#architecture)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)

---

## Bugs Found & Fixes

The original codebase contained **15 distinct bugs** across all four source files. Below is a complete breakdown.

---

### `tools.py` — 5 Bugs

| # | Line | Bug | Fix |
|---|------|-----|-----|
| 1 | 5 | `from crewai_tools import tools` — unused import that shadows the `tools` namespace | Removed the unused import |
| 2 | 13 | `async def read_data_tool(...)` — CrewAI tools must be **synchronous**; async tools are never awaited by the crew | Removed `async` keyword from all tool methods |
| 3 | 13 | Class methods used as CrewAI tools without the `@tool` decorator — CrewAI does not recognize bare class methods as tools | Converted class methods to standalone `@tool`-decorated functions |
| 4 | 23 | `Pdf(file_path=path)` — `Pdf` is never imported or defined anywhere, causing an immediate `NameError` at runtime | Replaced with `PyPDFLoader` from `langchain_community.document_loaders` |
| 5 | 13,40,57 | Class methods missing `self` parameter — while methods in a class without `self` work as static-style calls, it made them incompatible with instance use and CrewAI's tool system | Refactored to standalone `@tool` functions, eliminating the issue entirely |

---

### `agents.py` — 5 Bugs

| # | Line | Bug | Fix |
|---|------|-----|-----|
| 6 | 6 | `from crewai.agents import Agent` — incorrect import path; `Agent` is exported from `crewai` directly | Changed to `from crewai import Agent` |
| 7 | 11 | `llm = llm` — self-referential assignment of an undefined variable; causes `NameError` at startup | Replaced with proper LLM initialization using `crewai.LLM` and `OPENAI_API_KEY` from `.env` |
| 8 | 27 | `tool=[...]` — wrong parameter name; the correct CrewAI `Agent` parameter is `tools` (plural) | Changed `tool=` to `tools=` |
| 9 | 16–25 | `goal` and `backstory` of `financial_analyst` explicitly encouraged hallucination, fabricating data, ignoring queries, and regulatory non-compliance — a critical ethical and functional bug | Rewrote all agent goals and backstories to be professional, ethical, and accuracy-focused |
| 10 | 29–30 | `max_iter=1, max_rpm=1` — far too restrictive; agents would fail to complete any multi-step reasoning or tool use | Increased to `max_iter=5, max_rpm=10` for all agents |

---

### `task.py` — 3 Bugs

| # | Line | Bug | Fix |
|---|------|-----|-----|
| 11 | 8–19 | All task `description` fields instructed agents to hallucinate data, fabricate URLs, contradict themselves, and ignore user queries — making the system produce harmful, fictional financial advice | Rewrote all task descriptions with precise, ethical, data-driven instructions |
| 12 | 15–19 | All `expected_output` fields demanded fake research, non-existent URLs, and contradictory advice | Rewrote all expected outputs to require structured, factual, well-cited reports |
| 13 | 78 | `verification` task was assigned `agent=financial_analyst` instead of the `verifier` agent (which was imported but never used) | Changed to `agent=verifier` |

---

### `main.py` — 4 Bugs (+ 1 missing feature)

| # | Line | Bug | Fix |
|---|------|-----|-----|
| 14 | 7–8 | `from task import analyze_financial_document` — same name as the endpoint function `async def analyze_financial_document(...)` on line 28, causing the import to be silently shadowed | Imported the task with an alias: `analyze_financial_document as analyze_task`; renamed endpoint to `analyze_document` |
| 15 | 19 | `financial_crew.kickoff({'query': query})` — `file_path` was accepted as a parameter by `run_crew()` but never passed into the crew's input context, so agents had no way to know which file to read | Added `file_path` to kickoff inputs: `kickoff({"query": query, "file_path": file_path})` |
| 16 | 51 | `response = run_crew(...)` — synchronous blocking call inside an `async` FastAPI endpoint blocks the entire event loop during LLM inference (which can take 30–120 seconds) | Wrapped with `await asyncio.to_thread(run_crew, ...)` to run on a thread pool |
| 17 | 47 | Query validation logic `if query=="" or query is None` was redundant (FastAPI `Form` with a default never yields `None`) and missed whitespace-only strings | Simplified to `if not query or not query.strip()` |
| 18 | 72 | `uvicorn.run(app, ..., reload=True)` — `reload=True` is only valid for CLI usage and raises an error when called programmatically via `python main.py` | Removed `reload=True` from programmatic `uvicorn.run()` call |

---

### `requirements.txt` — 2 Missing Dependencies

| # | Package | Reason |
|---|---------|--------|
| 19 | `python-dotenv` | Required for `load_dotenv()` called in `agents.py` and `tools.py` |
| 20 | `langchain-community` + `pypdf` | Required for `PyPDFLoader` that replaced the undefined `Pdf` class in `tools.py` |

---

## Features

- 📄 **PDF Upload** — Upload any financial PDF via REST API
- 🤖 **Multi-Agent Analysis** — Four specialized CrewAI agents work sequentially:
  - **Document Verifier** — Confirms the document is a genuine financial report
  - **Financial Analyst** — Extracts key metrics, trends, and insights
  - **Investment Advisor** — Provides evidence-based BUY/HOLD/SELL recommendations
  - **Risk Assessor** — Evaluates market, credit, operational, and macro risks
- 🔍 **Web Search** — Agents can search the internet for current market context
- ⚡ **Async FastAPI** — Non-blocking API with thread-pool execution of crew tasks

---

## Architecture

```
User (HTTP)
    │
    ▼
FastAPI (/analyze endpoint)
    │  saves PDF → data/
    ▼
run_crew() [asyncio.to_thread]
    │
    ▼
CrewAI Crew (sequential process)
    ├── verifier          → verification task
    ├── financial_analyst → analyze_financial_document task
    ├── investment_advisor → investment_analysis task
    └── risk_assessor     → risk_assessment task
         │
         ▼
    Tools used by agents:
    ├── read_financial_document (@tool) — PyPDFLoader
    ├── search_tool (SerperDevTool)     — web search
    ├── analyze_investment (@tool)
    └── create_risk_assessment (@tool)
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- An OpenAI API key (or compatible LLM provider)
- A Serper API key (for web search via `SerperDevTool`) — optional but recommended

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd financial-document-analyzer-debug
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# Required — LLM provider
OPENAI_API_KEY=sk-...

# Optional — choose a different model (default: openai/gpt-4o-mini)
LLM_MODEL=gpt-4o-mini

# Optional — enables web search via SerperDevTool
SERPER_API_KEY=your_serper_key_here
```

### 5. Add a sample financial document

Download the Tesla Q2 2025 financial update:
```
https://www.tesla.com/sites/default/files/downloads/TSLA-Q2-2025-Update.pdf
```
Save it as `data/sample.pdf` (a copy is already included in `data/TSLA-Q2-2025-Update.pdf`).

### 6. Run the server

```bash
python main.py
```

Or with the Uvicorn CLI (with auto-reload for development):

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.

---

## Usage

### Via Swagger UI (recommended for testing)

Navigate to `http://localhost:8000/docs` for the interactive API explorer.

### Via curl

**Health check:**
```bash
curl http://localhost:8000/
```

**Analyze a financial document:**
```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@data/TSLA-Q2-2025-Update.pdf" \
  -F "query=What are the key revenue trends and investment risks for Tesla in Q2 2025?"
```

### Via Python

```python
import requests

with open("data/TSLA-Q2-2025-Update.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze",
        files={"file": ("TSLA-Q2-2025-Update.pdf", f, "application/pdf")},
        data={"query": "Summarize the financial performance and key risks."},
    )

print(response.json())
```

---

## API Documentation

### `GET /`

Health check endpoint.

**Response:**
```json
{
  "message": "Financial Document Analyzer API is running",
  "status": "healthy"
}
```

---

### `POST /analyze`

Upload a financial PDF and receive a comprehensive AI analysis.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | `file` (PDF) | ✅ Yes | The financial PDF document to analyze |
| `query` | `string` | ❌ No | Specific question or focus for the analysis. Default: `"Analyze this financial document for investment insights"` |

**Success Response (200):**
```json
{
  "status": "success",
  "query": "What are Tesla's key revenue trends?",
  "analysis": "## Financial Analysis Report\n\n### Executive Summary\n...",
  "file_processed": "TSLA-Q2-2025-Update.pdf"
}
```

**Error Response (400) — invalid file type:**
```json
{
  "detail": "Only PDF files are supported."
}
```

**Error Response (500) — processing error:**
```json
{
  "detail": "Error processing financial document: <error details>"
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | — | OpenAI API key for LLM access |
| `LLM_MODEL` | ❌ No | `openai/gpt-4o-mini` | LLM model identifier (CrewAI format) |
| `SERPER_API_KEY` | ❌ No | — | Serper.dev API key for web search |

---

## Project Structure

```
financial-document-analyzer-debug/
├── main.py           # FastAPI application & crew runner
├── agents.py         # CrewAI agent definitions
├── task.py           # CrewAI task definitions
├── tools.py          # Custom @tool functions (PDF reader, etc.)
├── requirements.txt  # Python dependencies
├── .env              # Environment variables (create this, do not commit)
├── data/
│   ├── TSLA-Q2-2025-Update.pdf   # Sample financial document
│   └── sample.pdf                # Default document path (add your own)
└── outputs/          # Reserved for future output storage
```

---

## Notes

- The uploaded PDF is automatically deleted from disk after processing.
- Analysis may take **30–120 seconds** depending on document length and LLM response times.
- The system uses a **sequential** CrewAI process: each agent's output is passed as context to the next.
- This tool is for **informational purposes only** and does not constitute personalized financial advice.
