#!/usr/bin/env python3
"""Test if /cargando route exists"""
import requests

s = requests.Session()

# Login first
print("[1] Logging in...")
r1 = s.post('http://localhost:5000/login', 
    data={'username': 'admin', 'password': 'admin'}, 
    allow_redirects=False)
print(f"    Login response: {r1.status_code}, Location: {r1.headers.get('Location', 'N/A')}")

# Try to access /cargando directly
print("[2] Accessing /cargando directly...")
try:
    r2 = s.get('http://localhost:5000/cargando', timeout=5, allow_redirects=False)
    print(f"    Response: {r2.status_code}")
    print(f"    Content-Type: {r2.headers.get('Content-Type', 'N/A')}")
    if r2.status_code == 200:
        print(f"    ✓ Contains 'Cargando': {'Cargando' in r2.text}")
        print(f"    ✓ Contains 'setTimeout': {'setTimeout' in r2.text}")
        if 'setTimeout' in r2.text:
            print(f"    Preview: {r2.text[r2.text.find('setTimeout')-50:r2.text.find('setTimeout')+150]}")
    else:
        print(f"    Content preview: {r2.text[:300]}")
except Exception as e:
    print(f"    Error: {e}")

# Also try accessing url_for to check what it generates
print("[3] Checking url_for resolution in Flask...")
from scenarios.BacktestWeb.app import create_app
app = create_app('admin')
with app.app_context():
    from flask import url_for
    try:
        url = url_for('main.cargando')
        print(f"    url_for('main.cargando') = {url}")
    except Exception as e:
        print(f"    ERROR: url_for failed: {e}")
