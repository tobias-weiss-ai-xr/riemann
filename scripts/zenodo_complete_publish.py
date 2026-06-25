"""
Completes Zenodo publishing by triggering publication.
"""

import requests

BASE_URL = "https://zenodo.org/api"
ZENODO_TOKEN = "48DrQ7p19Sk3zE018PanP42QsE5nB2znTwfpOKT68lz33b39KP7oywNwb3gp"
DEPOSIT_ID = "20555502"

HEADERS = {"Authorization": f"Bearer {ZENODO_TOKEN}"}

print("Publishing deposit...")
r = requests.post(
    f"{BASE_URL}/deposit/depositions/{DEPOSIT_ID}/actions/publish",
    headers=HEADERS
)

print(f"Status code: {r.status_code}")
print(f"Response: {r.text}")

if r.status_code == 202:
    print("\n✅ PUBLISHED!")
    print(f"DOI: 10.5281/zenodo.20555502")
    print(f"URL: https://zenodo.org/record/20555502")
else:
    print("\n❌ Publication failed")