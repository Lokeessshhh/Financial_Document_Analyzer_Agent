"""Quick test script to send the Tesla PDF to the /analyze endpoint."""
import requests

url = "http://127.0.0.1:8000/analyze"
pdf_path = "data/TSLA-Q2-2025-Update.pdf"
query = "Analyze Tesla Q2 2025 financial performance, key revenue metrics, investment potential and risks."

print(f"Sending {pdf_path} to {url} ...")

with open(pdf_path, "rb") as f:
    response = requests.post(
        url,
        files={"file": ("TSLA-Q2-2025-Update.pdf", f, "application/pdf")},
        data={"query": query},
    )

print(f"Status: {response.status_code}")
print(f"Response:\n{response.json()}")
