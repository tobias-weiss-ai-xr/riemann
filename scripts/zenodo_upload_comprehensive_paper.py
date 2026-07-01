"""
Zenodo upload for comprehensive GNN × Number Theory paper.

Uploads the full paper PDF and all figure assets to a new Zenodo deposit
via the legacy deposit API (avoids the v14 DOI deadlock).

Usage:
    python scripts/zenodo_upload_comprehensive_paper.py

After running, verify the deposit at the printed URL, then publish:
    python scripts/zenodo_upload_comprehensive_paper.py --publish <deposit_id>
"""

import argparse
import requests
from pathlib import Path

BASE_URL = "https://zenodo.org/api"
ZENODO_TOKEN = "48DrQ7p19Sk3zE018PanP42QsE5nB2znTwfpOKT68lz33b39KP7oywNwb3gp"

HEADERS = {"Authorization": f"Bearer {ZENODO_TOKEN}"}

# Paths relative to project root
PAPER_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = PAPER_ROOT / "paper" / "machine-learning-modular-forms-comprehensive.pdf"
FIGURES_DIR = PAPER_ROOT / "figures" / "cm_paper"

ABSTRACT = (
    "We investigate whether machine learning on Hecke eigenvalue data can distinguish "
    "complex multiplication (CM) from non-CM modular forms, and explore broader spectral "
    "properties of L-functions. Using 53,000 weight-2 newforms from the LMFDB, we conduct "
    "a comprehensive ML study spanning 16 experiments and 4 dedicated task suites.\n\n"
    "Key findings:\n"
    "• CM/non-CM classification achieves F1=0.970 using Hecke traces as bag-of-features.\n"
    "• GNN approaches on SL(2,F_p) Cayley graphs fail (R²<0) due to vertex-transitivity—"
    "local subgraph features carry zero information about global spectral properties.\n"
    "• Neural networks (CNN, Transformer, CNN+Attention) do not outperform gradient-boosted "
    "trees for rank prediction (0.52 accuracy), confirming a signal rather than model limitation.\n"
    "• L-function zero spacing is highly predictable from traces (std spacing R²=0.91), with "
    "a two-population structure: dimension-1 forms exhibit GUE statistics while higher "
    "dimensions approach Poisson.\n"
    "• Auxiliary targets (root number, order of vanishing, number of zeros) are trivially "
    "predictable (R²=1.0) from scalar features alone.\n"
    "• A novel dimension-dependent Brody parameter analysis reveals a monotonic gradient "
    "from β≈1.88 (d=1, GUE) to β≈0.13 (d≥6, Poisson), establishing a continuous "
    "spectral rigidity crossover.\n\n"
    "Our results demonstrate that while ML on arithmetic data can reproduce known theorems "
    "and detect fine-grained spectral structure, rank prediction remains fundamentally "
    "hard—consistent with theoretical expectations about the inscrutability of analytic rank."
)

KEYWORDS = [
    "modular forms",
    "Hecke eigenvalues",
    "complex multiplication",
    "machine learning",
    "graph neural networks",
    "L-functions",
    "Riemann hypothesis",
    "spectral gap",
    "LMFDB",
    "number theory",
    "GUE statistics",
    "Brody parameter",
    "zero spacing",
    "Cayley graphs",
    "SL(2, F_p)",
]

CREATORS = [{"name": "Weiss, Tobias", "affiliation": "Independent"}]

METADATA = {
    "metadata": {
        "title": "Machine Learning on Hecke Eigenvalues: From CM Detection to L-Function Spectral Properties",
        "upload_type": "publication",
        "publication_type": "preprint",
        "description": ABSTRACT,
        "creators": CREATORS,
        "keywords": KEYWORDS,
        "publication_date": "2026-07-01",
        "access_right": "open",
        "license": "cc-by-4.0",
        "related_identifiers": [
            {
                "identifier": "10.5281/zenodo.20510032",
                "relation": "isSupplementedBy",
                "resource_type": "dataset",
            }
        ],
    }
}

# Files to upload
FILES = [PDF_PATH] + sorted(FIGURES_DIR.glob("*.pdf")) + sorted(FIGURES_DIR.glob("*.png"))


def create_deposit():
    """Create a new deposit via the legacy API."""
    print("Creating deposit...")
    r = requests.post(f"{BASE_URL}/deposit/depositions", json={}, headers=HEADERS)
    r.raise_for_status()
    deposit = r.json()
    deposit_id = deposit["id"]
    doi = deposit["metadata"]["prereserve_doi"]["doi"]
    print(f"  Deposit ID: {deposit_id}")
    print(f"  DOI: {doi}")
    return deposit_id


def upload_files(deposit_id):
    """Upload all paper assets to the deposit."""
    print(f"\nUploading {len(FILES)} files...")
    for i, fpath in enumerate(FILES, 1):
        if not fpath.exists():
            print(f"  [{i}/{len(FILES)}] SKIPPED (not found): {fpath.name}")
            continue
        size_mb = fpath.stat().st_size / (1024 * 1024)
        print(f"  [{i}/{len(FILES)}] Uploading {fpath.name} ({size_mb:.1f} MB)...", end=" ", flush=True)
        with open(fpath, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/deposit/depositions/{deposit_id}/files",
                headers=HEADERS,
                files={"file": (fpath.name, f, "application/octet-stream")},
            )
        if r.status_code == 201:
            print("OK")
        else:
            print(f"FAILED ({r.status_code}: {r.text[:200]})")
            r.raise_for_status()


def set_metadata(deposit_id):
    """Set deposit metadata."""
    print("\nSetting metadata...")
    r = requests.put(
        f"{BASE_URL}/deposit/depositions/{deposit_id}",
        json=METADATA,
        headers=HEADERS,
    )
    r.raise_for_status()
    print("  Metadata set")


def publish_deposit(deposit_id):
    """Publish the deposit (irreversible)."""
    print(f"\nPublishing deposit {deposit_id}...")
    r = requests.post(
        f"{BASE_URL}/deposit/depositions/{deposit_id}/actions/publish",
        headers=HEADERS,
    )
    if r.status_code == 202:
        data = r.json()
        doi = data.get("doi", "unknown")
        print(f"  PUBLISHED! DOI: {doi}")
        print(f"  URL: https://zenodo.org/record/{deposit_id}")
    else:
        print(f"  FAILED ({r.status_code}: {r.text[:300]})")


def main():
    parser = argparse.ArgumentParser(description="Upload comprehensive paper to Zenodo")
    parser.add_argument("--publish", metavar="ID", help="Publish an existing deposit by ID")
    parser.add_argument("--create-only", action="store_true", help="Create deposit and upload, but skip metadata")
    parser.add_argument("--skip-upload", action="store_true", help="Only set metadata on existing deposit")
    args = parser.parse_args()

    if args.publish:
        publish_deposit(args.publish)
        return

    # Verify PDF exists
    if not PDF_PATH.exists():
        print(f"ERROR: Paper PDF not found at {PDF_PATH}")
        print("Run 'make paper-pdf' first.")
        return

    deposit_id = create_deposit()

    if not args.skip_upload:
        upload_files(deposit_id)

    if not args.create_only:
        set_metadata(deposit_id)

    print(f"\n{'='*60}")
    print(f"Deposit ready for review:")
    print(f"  URL: https://zenodo.org/deposit/{deposit_id}")
    print(f"\nTo publish, run:")
    print(f"  python scripts/zenodo_upload_comprehensive_paper.py --publish {deposit_id}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
