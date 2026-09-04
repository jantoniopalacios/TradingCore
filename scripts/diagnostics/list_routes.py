#!/usr/bin/env python3
"""List all registered routes in Flask"""
from scenarios.BacktestWeb.app import create_app

app = create_app('admin')

print("Registered routes in Flask:")
print("=" * 80)
for rule in app.url_map.iter_rules():
    if 'main' in str(rule):
        print(f"{str(rule):50} -> {rule.endpoint}")

print("\n" + "=" * 80)
print("Looking for 'cargando' endpoint:")
cargando_found = any('cargando' in str(rule) for rule in app.url_map.iter_rules())
if cargando_found:
    print("✓ 'cargando' found in routes")
else:
    print("✗ 'cargando' NOT found in routes")
