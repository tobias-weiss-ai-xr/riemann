#!/usr/bin/env python3
"""Test network connectivity from Docker container."""

import socket
import sys

print("Testing DNS resolution...", file=sys.stderr)
try:
    result = socket.getaddrinfo("www.lmfdb.org", 443)
    print(f"DNS OK: {result[0][4]}", file=sys.stderr)
except Exception as e:
    print(f"DNS FAILED: {e}", file=sys.stderr)

try:
    import urllib.request

    print("Testing HTTPS...", file=sys.stderr)
    r = urllib.request.urlopen("https://www.lmfdb.org/api/", timeout=15)
    print(f"HTTPS OK: status={r.status}", file=sys.stderr)
    data = r.read()
    print(f"Response length: {len(data)}", file=sys.stderr)
    print(f"First 200 chars: {data[:200]}", file=sys.stderr)
except Exception as e:
    print(f"HTTPS FAILED: {e}", file=sys.stderr)

try:
    import requests

    print("Testing requests...", file=sys.stderr)
    r = requests.get("https://www.lmfdb.org/api/", timeout=15)
    print(f"requests OK: status={r.status_code}", file=sys.stderr)
    print(f"First 200 chars: {r.text[:200]}", file=sys.stderr)
except Exception as e:
    print(f"requests FAILED: {e}", file=sys.stderr)
