#!/usr/bin/env python3
"""Upload paper to Zenodo via legacy API"""
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
PAPER_PATH = Path(__file__).parent.parent / 'paper' / 'arxiv' / 'paper.pdf'

print(f'Uploading {PAPER_PATH} to deposit {DEPOSIT_ID}...')

with open(PAPER_PATH, 'rb') as f:
    r = requests.post(
        f'{BASE}/deposit/depositions/{DEPOSIT_ID}/files',
        headers=HEADERS,
        files={'file': ('paper.pdf', f, 'application/pdf')}
    )

if r.status_code == 201:
    result = r.json()
    print('✓ Upload successful!')
    print(f"  File ID: {result['id']}")
    print(f"  Filename: {result['filename']}")
    print(f"  Size: {result['filesize']} bytes")
else:
    print(f'✗ Upload failed: {r.status_code}')
    print(r.text)
    exit(1)