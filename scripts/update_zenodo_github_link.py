"""
Update Zenodo record with GitHub repository link.

Adds GitHub repository URL to existing Zenodo record.
"""

import requests

BASE_URL = "https://zenodo.org/api"
ZENODO_TOKEN = "48DrQ7p19Sk3zE018PanP42QsE5nB2znTwfpOKT68lz33b39KP7oywNwb3gp"
RECORD_ID = "20555502"

HEADERS = {"Authorization": f"Bearer {ZENODO_TOKEN}"}

# Get current record
print("Fetching current record...")
r_get = requests.get(f"{BASE_URL}/records/{RECORD_ID}", headers=HEADERS)
r_get.raise_for_status()
record = r_get.json()

# Add GitHub URL to description
github_url = "https://github.com/tobias-weiss-ai-xr/riemann"
current_description = record.get("metadata", {}).get("description", "")

if github_url not in current_description:
    new_description = f"{current_description}\n\n\nGitHub Repository: {github_url}"
    
    metadata = {
        "metadata": {
            **record.get("metadata", {}),
            "description": new_description
        }
    }
    
    print(f"Updating record {RECORD_ID} with GitHub link...")
    r_patch = requests.patch(
        f"{BASE_URL}/records/{RECORD_ID}",
        json=metadata,
        headers=HEADERS
    )
    
    if r_patch.status_code in [200, 202]:
        print(f"Updated! GitHub link added to record {RECORD_ID}")
        print(f"View: https://zenodo.org/records/{RECORD_ID}")
    else:
        print(f"Update failed: {r_patch.status_code}")
        print(r_patch.text)
else:
    print("OK: GitHub link already present in record")