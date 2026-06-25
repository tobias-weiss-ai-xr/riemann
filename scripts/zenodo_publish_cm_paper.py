"""
Zenodo publisher for CM paper.

Reads: papers/cm-arxiv/paper.pdf, papers/cm-arxiv/abstract.txt, papers/cm-arxiv/keywords.txt
Creates: Zenodo deposit via legacy API
"""

import requests
from pathlib import Path

BASE_URL = "https://zenodo.org/api"
ZENODO_TOKEN = "48DrQ7p19Sk3zE018PanP42QsE5nB2znTwfpOKT68lz33b39KP7oywNwb3gp"

HEADERS = {"Authorization": f"Bearer {ZENODO_TOKEN}"}

# Read metadata
abstract = Path("papers/cm-arxiv/abstract.txt").read_text()
keywords = Path("papers/cm-arxiv/keywords.txt").read_text().strip().split("\n")

# Create deposit
print("Creating deposit...")
r = requests.post(f"{BASE_URL}/deposit/depositions", json={}, headers=HEADERS)
r.raise_for_status()
deposit = r.json()
deposit_id = deposit["id"]
doi = deposit["metadata"]["prereserve_doi"]["doi"]
print(f"Deposit ID: {deposit_id}")
print(f"DOI: {doi}")

# Upload PDF
print("Uploading paper.pdf...")
pdf_path = Path("papers/cm-arxiv/paper.pdf")
files = {"file": ("paper.pdf", pdf_path.open("rb"), "application/pdf")}
r_upload = requests.post(
    f"{BASE_URL}/deposit/depositions/{deposit_id}/files",
    headers=HEADERS,
    files=files
)
r_upload.raise_for_status()
print("PDF uploaded")

# Set metadata
print("Setting metadata...")
metadata = {
    "metadata": {
        "title": "Data-Driven Detection of Complex Multiplication in Weight 2 Cusp Forms",
        "upload_type": "publication",
        "publication_type": "preprint",
        "description": abstract,
        "creators": [{"name": "Weiss, Tobias", "affiliation": "Independent"}],
        "keywords": keywords,
        "publication_date": "2026-06-05",
        "access_right": "open"
    }
}

r_metadata = requests.put(
    f"{BASE_URL}/deposit/depositions/{deposit_id}",
    json=metadata,
    headers=HEADERS
)
r_metadata.raise_for_status()
print("Metadata set")

print(f"\nDeposit ready: https://zenodo.org/deposit/{deposit_id}")
print("Publish via: POST /api/deposit/depositions/{deposit_id}/actions/publish")