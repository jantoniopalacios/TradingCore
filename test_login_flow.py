#!/usr/bin/env python3
"""Test login flow to verify cargando redirects and delay_ms renders"""
import requests
import re

s = requests.Session()

# Test 1: Login
print("[TEST] Sending login...")
resp = s.post('http://localhost:5000/login', 
    data={'username': 'admin', 'password': 'admin'},
    allow_redirects=False,
    timeout=10)
print(f"  Response: {resp.status_code}")
print(f"  Location: {resp.headers.get('Location', 'N/A')}")

# Test 2: Follow redirect (should go to /cargando)
if resp.status_code in (301, 302, 303, 307, 308):
    next_url = resp.headers.get('Location')
    print(f"\n[TEST] Following redirect to: {next_url}")
    resp2 = s.get(f'http://localhost:5000{next_url}', timeout=10, allow_redirects=False)
    print(f"  Response: {resp2.status_code}")
    print(f"  Content length: {len(resp2.text)}")
    print(f"  Contains 'cargando': {'cargando' in resp2.text.lower()}")
    print(f"  Contains 'Cargando...': {'Cargando...' in resp2.text}")
    
    # Test 3: Check delay_ms rendering
    match = re.search(r'setTimeout\s*\([^,]+,\s*(\d+)', resp2.text)
    if match:
        delay = int(match.group(1))
        print(f"  ✓ setTimeout delay found: {delay}ms")
        if delay == 1200:
            print(f"    ✓ Delay is 1200ms for admin (correct)")
        else:
            print(f"    ⚠ Delay is {delay}ms but expected 1200ms for admin")
    else:
        print(f"  ✗ No setTimeout delay found in HTML")
        # Print snippet around script
        if 'setTimeout' in resp2.text:
            idx = resp2.text.find('setTimeout')
            print(f"    Context: ...{resp2.text[max(0,idx-50):idx+150]}...")
else:
    print(f"  ERROR: Login did not redirect (status {resp.status_code})")
