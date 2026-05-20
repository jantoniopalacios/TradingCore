#!/usr/bin/env python3
"""Create test app and list registered routes"""
from flask import Flask
from scenarios.BacktestWeb.routes.main_bp import main_bp

app = Flask(__name__)
app.register_blueprint(main_bp)

print("Routes registered in Flask app:")
print("="*80)
for rule in app.url_map.iter_rules():
    if rule.endpoint.startswith('main'):
        print(f"  {rule.rule:40} -> {rule.endpoint}")

print("\n" + "="*80)
cargando_rules = [r for r in app.url_map.iter_rules() if 'cargando' in r.rule]
if cargando_rules:
    print(f"✓ Found {len(cargando_rules)} route(s) with 'cargando':")
    for r in cargando_rules:
        print(f"    {r.rule}")
else:
    print("✗ NO routes with 'cargando' found")

print("\nAll main.* routes:")
main_routes = [r.rule for r in app.url_map.iter_rules() if r.endpoint.startswith('main')]
for r in sorted(main_routes):
    print(f"  {r}")
