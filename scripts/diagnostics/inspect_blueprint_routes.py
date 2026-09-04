#!/usr/bin/env python3
"""List blueprint route rules"""
from scenarios.BacktestWeb.routes.main_bp import main_bp

print("Blueprint deferred functions count:", len(main_bp.deferred_functions))
print("\nAttempting to extract route info from blueprint...")

# Iterate through deferred functions to see route rules
for rule_obj in main_bp.url_map.iter_rules():
    print(f"  {rule_obj.rule:40} -> {rule_obj.endpoint}")

print("\n" + "="*80)
if '/cargando' in [r.rule for r in main_bp.url_map.iter_rules()]:
    print("✓ /cargando route FOUND in blueprint")
else:
    print("✗ /cargando route NOT found in blueprint")

print("\nSearching for relevant routes:")
for rule in main_bp.url_map.iter_rules():
    if any(x in rule.rule for x in ['login', 'cargando', 'index', 'logout']):
        print(f"  {rule.rule} -> {rule.endpoint}")
