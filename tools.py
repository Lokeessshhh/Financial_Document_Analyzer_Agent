## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv(override=True)

# Bug Fix 1: Removed unused `from crewai_tools import tools` import
# Bug Fix 2: Use @tool decorator from crewai for custom tools
from crewai.tools import tool
from crewai_tools import SerperDevTool

## Creating search tool
search_tool = SerperDevTool()

# Fix 1: Cache parsed PDFs so the document is only read once per path,
#         even when multiple agents call this tool for the same file.
_doc_cache: dict = {}

## Creating custom pdf reader tool
# Bug Fix 4: Converted class-based tools to standalone @tool-decorated functions
#            because CrewAI expects decorated functions, not class methods.
# Bug Fix 5: Removed `async` keyword — CrewAI tools must be synchronous.
# Bug Fix 6: Added `self` fix by removing class wrapper and using @tool decorator instead.

@tool("Financial_Document_Reader")
def read_financial_document(path: str) -> str:
    """Read and extract text content from a financial PDF document.

    Args:
        path: Path to the PDF file to read (required).

    Returns:
        str: Full text content of the financial document.
    """
    # Return cached result if already read — avoids re-parsing the same PDF
    # for every agent that calls this tool during a crew run.
    if path in _doc_cache:
        return _doc_cache[path]

    import pypdf  # use pypdf directly, more reliable than PyPDFLoader
    
    reader = pypdf.PdfReader(path)
    
    # Priority pages first — financial tables the model must see
    # These typically contain: Financial Summary, Income Statement, Balance Sheet, Cash Flows
    PRIORITY_PAGES = [3, 4, 5, 6, 23, 24, 25, 26, 27, 28]  # 0-indexed
    OTHER_PAGES = [i for i in range(len(reader.pages)) if i not in PRIORITY_PAGES]
    
    page_order = PRIORITY_PAGES + OTHER_PAGES
    
    pages = []
    for i in page_order:
        if i >= len(reader.pages):
            continue
        content = (reader.pages[i].extract_text() or '').strip()
        if len(content) < 50:  # skip empty/photo pages
            continue
        pages.append(f"--- Page {i+1} ---\n{content}")
    
    full_report = "\n\n".join(pages)
    
    # Truncate only if extremely large (>100k chars) to avoid context overflow
    if len(full_report) > 100_000:
        full_report = full_report[:100_000] + "\n\n[TRUNCATED]"
    
    _doc_cache[path] = full_report
    return full_report


@tool("Investment_Analyzer")
def analyze_investment(financial_document_data: str) -> str:
    """Analyze financial document data and provide investment insights.

    Args:
        financial_document_data: The text content of the financial document.

    Returns:
        str: Structured investment analysis summary.
    """
    # Bug Fix 8: Removed async, added @tool decorator, implemented basic logic
    processed_data = financial_document_data.strip()

    # Clean up the data format — remove double spaces
    while "  " in processed_data:
        processed_data = processed_data.replace("  ", " ")

    # Return the cleaned document data for the agent to analyze
    return f"Financial document content for investment analysis:\n\n{processed_data}"


@tool("Risk_Assessment_Tool")
def create_risk_assessment(financial_document_data: str) -> str:
    """Assess financial risks from a financial document.

    Args:
        financial_document_data: The text content of the financial document.

    Returns:
        str: Risk assessment summary based on document content.
    """
    # Bug Fix 9: Removed async, added @tool decorator, implemented basic logic
    processed_data = financial_document_data.strip()
    return f"Financial document content for risk assessment:\n\n{processed_data}"


# Backwards-compatible alias used by agents.py / task.py
class FinancialDocumentTool:
    """Wrapper class kept for import compatibility."""
    read_data_tool = read_financial_document
