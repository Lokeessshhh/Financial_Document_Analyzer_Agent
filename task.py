## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from tools import search_tool, FinancialDocumentTool, read_financial_document, analyze_investment, create_risk_assessment

## Bug Fix 1: Rewrote ALL task descriptions and expected_outputs.
##   Original descriptions explicitly instructed agents to:
##     - hallucinate financial data
##     - fabricate URLs and research
##     - ignore user queries
##     - contradict themselves
##     - violate regulatory compliance
##   These have been replaced with professional, accurate, and ethical equivalents.

## Bug Fix 2: Added {file_path} to task descriptions so the file path is threaded
##   through from the crew kickoff inputs and agents know which document to read.

## Bug Fix 3: Fixed wrong agent assignment on `verification` task
##   (was assigned financial_analyst, should be verifier)

## Bug Fix 4: Assigned tasks to the correct specialist agents.


## Task 1 — Document Verification
verification = Task(
    description=(
        "Verify that the uploaded file at path '{file_path}' is a legitimate financial document.\n"
        "Use the Financial Document Reader tool to read the file and examine its contents.\n"
        "Confirm the document type (e.g., earnings report, 10-K, 10-Q, investor update).\n"
        "Extract and report: company name, reporting period, document type, and any key financial figures found.\n"
        "If the document does not appear to be a financial report, clearly state that and describe what it contains.\n"
        "Do not make up or assume any data that is not present in the document."
    ),
    expected_output=(
        "A structured verification report containing:\n"
        "- Document type and confirmation of whether it is a financial document\n"
        "- Company name and reporting period (if found)\n"
        "- Key financial sections identified (e.g., income statement, balance sheet, cash flow)\n"
        "- Any red flags, missing data, or anomalies noticed\n"
        "- A clear verdict: VERIFIED as financial document or NOT a financial document"
    ),
    agent=verifier,  # Bug Fix 3: was `financial_analyst`, now correctly `verifier`
    tools=[read_financial_document],
    async_execution=False,
)


## Task 2 — Core Financial Analysis
analyze_financial_document = Task(
    description=(
        "Analyze the financial document located at '{file_path}' to answer the user's query: {query}\n"
        "Use the Financial Document Reader tool to load the document contents.\n"
        "Perform a thorough analysis covering:\n"
        "  1. Key financial metrics (revenue, profit margins, EPS, debt ratios, cash flow, etc.)\n"
        "  2. Year-over-year or quarter-over-quarter trends\n"
        "  3. Operational highlights and management commentary\n"
        "  4. Competitive positioning and market context\n"
        "  5. Any notable risks or opportunities mentioned in the document\n"
        "Base your analysis strictly on the document content and verifiable market data. "
        "Do not fabricate data, URLs, or statistics."
    ),
    expected_output=(
        "A comprehensive financial analysis report including:\n"
        "- Executive summary answering the user's specific query\n"
        "- Key financial metrics with values extracted directly from the document\n"
        "- Trend analysis with comparisons to prior periods (if available)\n"
        "- Notable strengths and concerns identified in the document\n"
        "- Data-driven market insights supported by real sources\n"
        "- Clear, structured formatting with sections and bullet points"
    ),
    agent=financial_analyst,
    tools=[read_financial_document, search_tool],
    async_execution=False,
    context=[verification],
)


## Task 3 — Investment Analysis
investment_analysis = Task(
    description=(
        "Based on the financial document at '{file_path}' and the user's query: {query},\n"
        "provide evidence-based investment recommendations.\n"
        "Use the Financial Document Reader tool to review the document.\n"
        "Your analysis should include:\n"
        "  1. Valuation assessment (P/E, P/B, EV/EBITDA if applicable) — ONLY if you have current market price data. "
        "Do NOT calculate or estimate these ratios without actual stock price information.\n"
        "  2. Growth prospects based on documented financials\n"
        "  3. Dividend and capital allocation analysis (if applicable)\n"
        "  4. Comparison with industry benchmarks\n"
        "  5. Clear BUY / HOLD / SELL recommendation with rationale\n"
        "All recommendations must be grounded in the actual document data. "
        "Disclose that this is for informational purposes only and not personalized financial advice."
    ),
    expected_output=(
        "A structured investment recommendation report including:\n"
        "- Investment thesis summary\n"
        "- Valuation metrics with calculations and sources\n"
        "- Growth and profitability outlook\n"
        "- BUY / HOLD / SELL recommendation with clear data-backed rationale\n"
        "- Key risks to the investment thesis\n"
        "- Disclaimer: For informational purposes only, not personalized financial advice"
    ),
    agent=investment_advisor,  # Bug Fix 4: assigned to proper specialist agent
    tools=[read_financial_document, analyze_investment],
    async_execution=False,
    context=[analyze_financial_document],
)


## Task 4 — Risk Assessment
risk_assessment = Task(
    description=(
        "Conduct a comprehensive risk assessment based on the financial document at '{file_path}'.\n"
        "User query context: {query}\n"
        "Use the Financial Document Reader tool to examine the document.\n"
        "Evaluate the following risk categories based on actual document data:\n"
        "  1. Market risk (revenue volatility, pricing power, demand sensitivity)\n"
        "  2. Credit and liquidity risk (debt levels, cash runway, credit ratings)\n"
        "  3. Operational risk (supply chain, regulatory, execution risk)\n"
        "  4. Macro risk (interest rates, inflation, geopolitical factors mentioned)\n"
        "  5. ESG and regulatory risk (if disclosed)\n"
        "Assign a risk rating (Low / Medium / High) to each category with justification. "
        "Do not invent risk factors not supported by the document."
    ),
    expected_output=(
        "A structured risk assessment report including:\n"
        "- Overall risk rating (Low / Medium / High) with summary justification\n"
        "- Risk breakdown by category with individual ratings and evidence from the document\n"
        "- Top 3-5 key risk factors with mitigation strategies\n"
        "- Risk monitoring indicators to watch going forward\n"
        "- Conclusion with balanced risk/reward perspective"
    ),
    agent=risk_assessor,  # Bug Fix 4: assigned to proper specialist agent
    tools=[read_financial_document, create_risk_assessment],
    async_execution=False,
    context=[analyze_financial_document],
)
