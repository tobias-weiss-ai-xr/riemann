#!/usr/bin/env python3
"""Publish Zenodo deposit"""
import requests
from pathlib import Path

# Load token from .env
env_file = Path(__file__).parent.parent / '.env'
with open(env_file, 'r') as f:
    for line in f:
        if line.startswith('ZENODO_TOKEN='):
            token = line.split('=', 1)[1].strip()
            break

BASE = 'https://zenodo.org/api'
HEADERS = {'Authorization': f'Bearer {token}'}

DEPOSIT_ID = 20510032

print(f'Publishing deposit {DEPOSIT_ID}...')
print(f'This will assign DOI: 10.5281/zenodo.20510032')

r = requests.post(
    f'{BASE}/deposit/depositions/{DEPOSIT_ID}/actions/publish',
    headers=HEADERS
)

if r.status_code == 202:
    result = r.json()
    print('✓ Publication successful!')
    print(f"  DOI: {result['doi']}")
    print(f"  Concept DOI: {result['conceptdoi']}")
    print(f"  Record URL: {result['record_url']}")
    print(f"  Created: {result['created']}")
else:
    print(f'✗ Publication failed: {r.status_code}')
    print(r.text)
    exit(1)