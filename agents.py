## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from crewai import Agent

# Bug Fix 1: Replaced `from crewai.agents import Agent` with `from crewai import Agent`
#            (crewai.agents is not the correct public import path)

from tools import FinancialDocumentTool, read_financial_document, analyze_investment, create_risk_assessment, search_tool

### Loading LLM
# Bug Fix 2: Replaced `llm = llm` (NameError — self-referential undefined variable)
#            with proper LLM initialization using the OpenAI provider via crewai's LLM wrapper.
#            Uses OPENAI_API_KEY from .env file. Change model/provider as needed.
from crewai import LLM

def _get_llm():
    """Lazy LLM instantiation using NVIDIA NIM via LiteLLM."""
    return LLM(
        model="nvidia_nim/meta/llama-3.3-70b-instruct",
        api_key=os.getenv("NVIDIA_API_KEY"),
    )

# Creating an Experienced Financial Analyst agent
# Bug Fix 3: Changed `tool=` (wrong parameter name) to `tools=` (correct CrewAI parameter)
# Bug Fix 4: Rewrote goal and backstory to be professional, ethical, and accurate
#            (original content encouraged hallucination, fraud, and regulatory non-compliance)
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

# Creating a document verifier agent
# Bug Fix 7: Rewrote goal and backstory to reflect a legitimate compliance/verification role
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


# Creating an Investment Advisor agent
# Bug Fix 8: Rewrote goal and backstory to be ethical and compliant
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


# Creating a Risk Assessor agent
# Bug Fix 9: Rewrote goal and backstory to reflect professional risk management practices
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
