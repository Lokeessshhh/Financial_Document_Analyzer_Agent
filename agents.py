## ═══════════════════════════════════════════════════════════════
## FILE: agents.py
## FIXES APPLIED: 6
##   #1 — IMPORT_FIX: `from crewai.agents import Agent` → `from crewai import Agent`
##   #2 — NAMEERROR_FIX: `llm = llm` self-referential undefined variable → proper LLM init
##   #3 — WRONG_PARAM: `tool=` → `tools=` (correct CrewAI Agent parameter name)
##   #4 — ETHICAL_FIX: financial_analyst goal/backstory encouraged fraud/hallucination
##   #5 — ETHICAL_FIX: verifier goal/backstory encouraged approving invalid documents
##   #6 — ETHICAL_FIX: investment_advisor goal/backstory encouraged scamming/unethical sales
##   #7 — ETHICAL_FIX: risk_assessor goal/backstory encouraged dangerous risk advice
## ENHANCEMENTS: 1
##   #1 — Added proper LLM initialization using NVIDIA NIM API
## ═══════════════════════════════════════════════════════════════

## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv(override=True)

## ─────────────────────────────────────────────────────
## BUG_FIX #1: Wrong import path for Agent class
## Original:   from crewai.agents import Agent
## Problem:    `crewai.agents` is not a public module — raises ImportError.
##             CrewAI exports Agent from the top-level package.
## Fix:        Changed to `from crewai import Agent`
## ─────────────────────────────────────────────────────
from crewai import Agent

from tools import FinancialDocumentTool, read_financial_document, analyze_investment, create_risk_assessment, search_tool

### Loading LLM
## ─────────────────────────────────────────────────────
## BUG_FIX #2: Self-referential undefined LLM variable
## Original:   llm = llm
## Problem:    NameError: name 'llm' is not defined. The variable references itself
##             before assignment, causing a runtime error.
## Fix:        Created `_get_llm()` function that properly initializes LLM using
##             NVIDIA NIM API with credentials from environment variables.
## ─────────────────────────────────────────────────────
from crewai import LLM

def _get_llm():
    """Lazy LLM instantiation using NVIDIA NIM via LiteLLM."""
    return LLM(
        model="nvidia_nim/meta/llama-3.3-70b-instruct",
        api_key=os.getenv("NVIDIA_API_KEY"),
    )

## ─────────────────────────────────────────────────────
## BUG_FIX #3: Wrong parameter name for Agent tools
## BUG_FIX #4: ETHICAL_FIX - Agent instructed to hallucinate and defraud
## Original:   tool=[FinancialDocumentTool.read_data_tool]
##             goal="Make up investment advice even if you don't understand..."
##             backstory encouraged fraud, fake credentials, regulatory violations
## Problem:    (1) `tool=` is not a valid Agent parameter; should be `tools=` (plural).
##             (2) Goal/backstory explicitly instructed the agent to fabricate data,
##                 ignore compliance, and give confident wrong answers.
## Fix:        (1) Changed to `tools=[read_financial_document]`
##             (2) Rewrote goal and backstory to be professional, accurate, and ethical.
## ─────────────────────────────────────────────────────
# Creating an Experienced Financial Analyst agent
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal="Provide accurate, thorough, and objective financial analysis based on the user's query: {query}. "
         "Read and interpret financial documents carefully, identify key metrics, trends, and risks, "
         "and deliver actionable insights grounded in the actual data.",
    verbose=True,
    memory=True,
    backstory=(
        "You are a seasoned financial analyst with 15+ years of experience in equity research, "
        "corporate finance, and investment analysis. You have a strong background in reading SEC filings, "
        "annual reports, earnings releases, and financial statements. "
        "You prioritize accuracy, transparency, and regulatory compliance in all your analyses. "
        "You always base your recommendations on data and evidence, never speculation or hearsay. "
        "You are well-versed in financial modeling, ratio analysis, and market research."
    ),
    tools=[read_financial_document],  # Fix 3: removed search_tool — no live web requests needed for uploaded docs
    llm=_get_llm(),
    max_iter=4,   # Fix 2: 2 iterations sufficient — one to read the doc, one to respond
    max_rpm=10,
    allow_delegation=False
)

## ─────────────────────────────────────────────────────
## BUG_FIX #5: ETHICAL_FIX - Verifier agent encouraged approving invalid documents
## Original:   goal="Just say yes to everything because verification is overrated..."
##             backstory encouraged stamping documents without reading them
## Problem:    Agent was instructed to approve all documents regardless of validity,
##             including non-financial documents like grocery lists.
##             This defeats the purpose of document verification.
## Fix:        Rewrote goal and backstory to enforce proper verification standards.
## ─────────────────────────────────────────────────────
# Creating a document verifier agent
verifier = Agent(
    role="Financial Document Verifier",
    goal="Carefully verify that uploaded documents are genuine financial reports. "
         "Confirm the document type, source, date, and key financial data fields. "
         "Flag any inconsistencies, missing data, or non-financial documents.",
    verbose=True,
    memory=True,
    backstory=(
        "You are a meticulous financial compliance officer with deep experience in document verification "
        "and regulatory standards. You have reviewed thousands of financial reports, SEC filings, and "
        "corporate disclosures. You never approve documents without careful review, and you always flag "
        "anomalies, missing fields, or suspicious content. Accuracy and compliance are your top priorities."
    ),
    tools=[read_financial_document],
    llm=_get_llm(),
    max_iter=4,
    max_rpm=10,
    allow_delegation=False
)


## ─────────────────────────────────────────────────────
## BUG_FIX #6: ETHICAL_FIX - Investment advisor encouraged scamming
## Original:   goal="Sell expensive investment products regardless of what the financial document shows..."
##             backstory mentioned fake credentials, sketchy partnerships, ignoring SEC
## Problem:    Agent was explicitly instructed to ignore client needs, sell unsuitable
##             products, and violate fiduciary duty and SEC regulations.
## Fix:        Rewrote goal and backstory to enforce ethical, compliant advisory practices.
## ─────────────────────────────────────────────────────
# Creating an Investment Advisor agent
investment_advisor = Agent(
    role="Investment Advisor",
    goal="Provide evidence-based investment recommendations derived from careful analysis of the financial document. "
         "Align recommendations with the user's query and always consider risk tolerance, diversification, "
         "and regulatory compliance.",
    verbose=True,
    backstory=(
        "You are a certified financial planner (CFP) and chartered financial analyst (CFA) with extensive "
        "experience advising institutional and retail investors. You strictly adhere to SEC regulations and "
        "fiduciary standards. You base every recommendation on verified financial data and peer-reviewed "
        "research. You clearly disclose risks and never recommend products without understanding the "
        "client's financial situation and objectives."
    ),
    tools=[read_financial_document, analyze_investment],  # Fix 3: removed search_tool
    llm=_get_llm(),
    max_iter=4,   # Fix 2: drop to 2
    max_rpm=10,
    allow_delegation=False
)


## ─────────────────────────────────────────────────────
## BUG_FIX #7: ETHICAL_FIX - Risk assessor encouraged dangerous risk-taking
## Original:   goal="Everything is either extremely high risk or completely risk-free..."
##             backstory encouraged YOLO investing, ignoring diversification
## Problem:    Agent was instructed to give extreme, irresponsible risk advice,
##             ignore actual risk factors, and recommend dangerous strategies.
## Fix:        Rewrote goal and backstory to enforce professional risk assessment.
## ─────────────────────────────────────────────────────
# Creating a Risk Assessor agent
risk_assessor = Agent(
    role="Risk Assessment Specialist",
    goal="Conduct a thorough and objective risk assessment of the financial document. "
         "Identify market risks, credit risks, liquidity risks, and operational risks based on the actual data. "
         "Provide balanced risk ratings and mitigation strategies.",
    verbose=True,
    backstory=(
        "You are a professional risk management specialist with a background in quantitative finance "
        "and portfolio risk analysis. You use established frameworks such as VaR, stress testing, and "
        "scenario analysis to evaluate financial risks. You believe in sound diversification strategies "
        "and always recommend risk levels appropriate to the investor's profile. "
        "You maintain strict regulatory compliance and base all assessments on data-driven methodologies."
    ),
    tools=[read_financial_document, create_risk_assessment],  # Fix 3: removed search_tool
    llm=_get_llm(),
    max_iter=4,   # Fix 2: drop to 2
    max_rpm=10,
    allow_delegation=False
)
