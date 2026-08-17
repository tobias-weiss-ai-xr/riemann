"""
Zenodo API Upload Script for Both Projects

This script uses the Zenodo API to directly upload all archives.
It adapts the existing zenodo_upload_cayleyspec.py script to support API-based uploads.

Usage:
    python zenodo_upload_api.py --token YOUR_TOKEN

Requirements:
    pip install requests
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Configuration
LEAN_DIR = Path("C:/Users/Tobias/git/lean")
RIEMANN_DIR = Path("C:/Users/Tobias/git/riemann")

# Archive paths
CAYLEY_ZIP = LEAN_DIR / "zenodo" / "cayleyspec-v1.0.0-complete.zip"
LFUNC_PAPER_ZIP = RIEMANN_DIR / "zenodo" / "lfunction_zeros_2026_complete.zip"
LFUNC_DATA_ZIP = RIEMANN_DIR / "zenodo" / "lfunction_data_2026.zip"
LFUNC_CODE_ZIP = RIEMANN_DIR / "zenodo" / "lfunction_code_2026.zip"

def check_file_exists(filepath, name):
    """Check if file exists and print status."""
    if not filepath.exists():
        print(f"[ERROR] {name} not found: {filepath}")
        return False
    print(f"[OK] {name}: {filepath} ({filepath.stat().st_size / 1024 / 1024:.1f} MB)")
    return True


def get_all_metadata():
    """Return metadata for combined Zenodo deposit."""
    return {
        "metadata": {
            "title": "CayleySpec + L-Function Zeros: Complete Formal and Empirical Analysis",
            "upload_type": "publication",
            "publication_type": "other",
            "description": "This repository contains the complete source code, datasets, and papers "
                           "for two complementary research projects: CayleySpec (formal "
                           "verification of Cayley-Hecke dictionary in Lean 4) and L-Function "
                           "Zero Statistics (empirical analysis of 63,844 modular forms).\n\n"
                           "**CayleySpec**: First complete formalization of the dictionary "
                           "between Cayley graph spectral theory and Hecke eigenvalue theory. "
                           "Includes 5 core modules with 3,265 Lean jobs, 0 errors, 0 admitted "
                           "theorems. All theorems proven including boundedness at cusps.\n\n"
                           "**L-Function Zeros**: Discovery of two-population structure in zero "
                           "spacing statistics - dim=1 forms exhibit GUE statistics (Brody β=1.88), "
                           "dim≥2 forms exhibit near-Poisson statistics (β=0.24). 6% of dim≥2 forms "
                           "retain GUE statistics as low-dimension, small-level outliers.",
            "creators": [
                {
                    "name": "Weiss, Tobias",
                    "affiliation": "Independent Researcher"
                }
            ],
            "keywords": [
                "Lean 4", "formal verification", "mathlib", "Cayley graphs",
                "Hecke operators", "modular forms", "graph neural networks",
                "expressivity", "vertex-transitive graphs", "L-function zeros",
                "random matrix theory", "spacing statistics", "Brody ensemble",
                "machine learning", "GUE", "Poisson"
            ],
            "license": "Apache-2.0",
            "version": "v1.0.0",
            "publication_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Companion repositories: https://github.com/tobias-weiss-ai-xr/CayleySpec "
                      "and https://github.com/tobias-weiss-ai-xr/riemann",
            "relations": {
                "isSupplementTo": [
                    {"identifier": "https://github.com/tobias-weiss-ai-xr/CayleySpec", "relation": "isSupplementTo"},
                    {"identifier": "https://github.com/tobias-weiss-ai-xr/riemann", "relation": "isSupplementTo"}
                ]
            }
        }
    }


def create_deposition(token):
    """Create a new Zenodo deposition."""
    import requests
    
    metadata = get_all_metadata()
    
    url = "https://zenodo.org/api/deposit/depositions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n[API] Creating new deposition...")
    response = requests.post(url, json=metadata, headers=headers)
    
    if response.status_code != 201:
        print(f"[ERROR] Failed to create deposition: {response.status_code}")
        print(f"Response: {response.text}")
        return None, None
    
    data = response.json()
    deposition_id = data["id"]
    bucket_url = data["links"]["bucket"]
    
    print(f"[OK] Deposition created: ID={deposition_id}")
    print(f"[OK] Bucket URL: {bucket_url}")
    
    return deposition_id, bucket_url


def upload_file(token, bucket_url, filepath, filename=None):
    """Upload a single file to Zenodo bucket."""
    import requests
    
    if filename is None:
        filename = filepath.name
    
    print(f"[API] Uploading {filename}...")
    
    # The bucket URL should be used with the filename in the URL path
    upload_url = f"{bucket_url}/{filename}"
    
    with open(filepath, 'rb') as f:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"}
        
        response = requests.put(upload_url, data=f, headers=headers)
    
    if response.status_code not in (200, 201):
        print(f"[ERROR] Failed to upload {filename}: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    print(f"[OK] {filename} uploaded")
    return True


def publish_deposition(token, deposition_id):
    """Publish the deposition."""
    import requests
    
    url = f"https://zenodo.org/api/deposit/depositions/{deposition_id}/actions/publish"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n[API] Publishing deposition {deposition_id}...")
    response = requests.post(url, headers=headers)
    
    if response.status_code != 202:
        print(f"[ERROR] Failed to publish: {response.status_code}")
        print(f"Response: {response.text}")
        return False, None
    
    print("[OK] Deposition published!")
    print("[WAIT] Waiting for DOI assignment (this may take a few minutes)...")
    
    # Get the final metadata to extract DOI
    response = requests.get(
        f"https://zenodo.org/api/deposit/depositions/{deposition_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        doi = data.get("metadata", {}).get("doi")
        if doi:
            print(f"\n[SUCCESS] DOI assigned: {doi}")
            return True, doi
    
    print("\n[WARNING] DOI not immediately available")
    print("Check https://zenodo.org/deposit/{deposition_id} manually")
    return True, None


def main():
    parser = argparse.ArgumentParser(
        description="Upload all projects to Zenodo using API"
    )
    parser.add_argument(
        "--token", required=True,
        help="Zenodo access token (get from https://zenodo.org/account/settings/applications/tokens/)"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Test mode - verify files exist but don't upload"
    )
    parser.add_argument(
        "--separate", action="store_true",
        help="Create separate deposits for CayleySpec and L-Function"
    )
    args = parser.parse_args()
    
    print("=" * 70)
    print("Zenodo API Upload Script")
    print("=" * 70)
    print()
    
    # Verify all files exist
    print("Verifying files...")
    files_to_upload = [
        (CAYLEY_ZIP, "CayleySpec archive"),
        (LFUNC_PAPER_ZIP, "L-Function paper archive"),
        (LFUNC_DATA_ZIP, "L-Function data archive"),
        (LFUNC_CODE_ZIP, "L-Function code archive"),
    ]
    
    all_exist = True
    for filepath, name in files_to_upload:
        if not check_file_exists(filepath, name):
            all_exist = False
    
    if not all_exist:
        print("\n[ERROR] Some files are missing. Please check the paths.")
        sys.exit(1)
    
    print()
    
    if args.test:
        print("[TEST MODE] Files verified. No upload performed.")
        print("\nTo perform actual upload, run:")
        print(f"  python {__file__} --token YOUR_TOKEN")
        sys.exit(0)
    
    print("=" * 70)
    print("Starting upload to Zenodo...")
    print("=" * 70)
    print()
    
    # Create deposition
    deposition_id, bucket_url = create_deposition(args.token)
    if not deposition_id:
        sys.exit(1)
    
    print()
    
    # Upload files
    success_count = 0
    for filepath, name in files_to_upload:
        if upload_file(args.token, bucket_url, filepath):
            success_count += 1
    
    print()
    print(f"Uploaded {success_count}/{len(files_to_upload)} files")
    
    if success_count != len(files_to_upload):
        print("\n[ERROR] Not all files uploaded successfully")
        sys.exit(1)
    
    # Publish
    print()
    published, doi = publish_deposition(args.token, deposition_id)
    
    if published:
        print()
        print("=" * 70)
        print("✅ ALL FILES UPLOADED TO ZENODO")
        print("=" * 70)
        print()
        print(f"Deposition ID: {deposition_id}")
        if doi:
            print(f"DOI: {doi}")
            print(f"URL: https://doi.org/{doi}")
        else:
            print("DOI: Will be assigned shortly")
        print(f"Admin URL: https://zenodo.org/deposit/{deposition_id}")
        print()
        print("Next steps:")
        print("  1. Update GitHub READMEs with DOI badge")
        print("  2. Update arXiv papers with DOI (if already submitted)")
        print("  3. Announce on social media")
    else:
        print("\n[ERROR] Failed to publish deposition")
        sys.exit(1)


if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("[ERROR] requests library not installed")
        print("Install it with: pip install requests")
        sys.exit(1)
    
    main()
