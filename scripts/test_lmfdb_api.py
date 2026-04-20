#!/usr/bin/env python3
"""Test LMFDB API structure and pagination."""

import requests
import json
import time

BASE = "https://www.lmfdb.org/api"


def test_endpoint(url, params=None, desc=""):
    print(f"\n{'=' * 60}")
    print(f"  {desc}")
    print(f"  URL: {url}")
    if params:
        print(f"  Params: {params}")
    print("=" * 60)
    try:
        r = requests.get(url, params=params, timeout=30)
        print(f"  Status: {r.status_code}")
        d = r.json()
        if isinstance(d, dict):
            print(f"  Top-level keys: {sorted(d.keys())}")
            if "count" in d:
                print(f"  Total count: {d['count']}")
            if "newforms" in d:
                print(f"  Newforms returned: {len(d['newforms'])}")
                if d["newforms"]:
                    first = d["newforms"][0]
                    print(f"  First newform label: {first.get('label')}")
                    print(f"  First newform fields: {sorted(first.keys())}")
                    print(
                        f"  Sample data: {json.dumps({k: first[k] for k in ['label', 'level', 'weight', 'dim', 'analytic_rank', 'char_order'] if k in first}, indent=2)}"
                    )
            if "hecke_eigenvalues" in d:
                print(f"  Hecke eigenvalues count: {len(d['hecke_eigenvalues'])}")
                if d["hecke_eigenvalues"]:
                    print(f"  First 5: {d['hecke_eigenvalues'][:5]}")
            if "eigenvalues" in d:
                print(f"  Eigenvalues count: {len(d['eigenvalues'])}")
                if d["eigenvalues"]:
                    print(f"  First 5: {d['eigenvalues'][:5]}")
        else:
            print(f"  Response type: {type(d)}, length: {len(d)}")
            print(f"  First 500 chars: {json.dumps(d, indent=2)[:500]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    time.sleep(0.5)  # Be polite


# Test 1: Count weight-2 newforms
test_endpoint(
    f"{BASE}/mf_newforms/",
    {"weight": "i2", "count": "0"},
    "Count all weight-2 newforms",
)

# Test 2: Get 3 newforms
test_endpoint(
    f"{BASE}/mf_newforms/", {"weight": "i2", "count": "3"}, "Get 3 weight-2 newforms"
)

# Test 3: Get 3 newforms with prime level
test_endpoint(
    f"{BASE}/mf_newforms/",
    {"weight": "i2", "level_type": "prime", "count": "3"},
    "Get 3 weight-2 newforms (prime level only)",
)

# Test 4: Hecke eigenvalues for a known newform
test_endpoint(
    f"{BASE}/mf_hecke_cc/",
    {"label": "11.2.a.a", "n": "pyrange(1,20)"},
    "Hecke eigenvalues for 11.2.a.a",
)

# Test 5: Hecke eigenvalues (real form)
test_endpoint(
    f"{BASE}/mf_hecke_nf/",
    {"label": "11.2.a.a", "n": "pyrange(1,20)"},
    "Hecke eigenvalues (number field) for 11.2.a.a",
)

# Test 6: L-function zeros
test_endpoint(
    f"{BASE}/lfunc_lfunctions/",
    {"conductor": "i11", "character": "0", "weight": "i2"},
    "L-function for level 11",
)

# Test 7: Pagination - offset
test_endpoint(
    f"{BASE}/mf_newforms/",
    {"weight": "i2", "count": "2", "offset": "1000"},
    "Newforms with offset=1000",
)

# Test 8: Check rate limit headers
print("\n" + "=" * 60)
print("  Rate limit headers check")
print("=" * 60)
r = requests.get(
    f"{BASE}/mf_newforms/", params={"weight": "i2", "count": "1"}, timeout=30
)
for k, v in r.headers.items():
    if "rate" in k.lower() or "limit" in k.lower() or "remaining" in k.lower():
        print(f"  {k}: {v}")
print("  (empty = no rate limit headers)")

print("\n\nDONE.")
