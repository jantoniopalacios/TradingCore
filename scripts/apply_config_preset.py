"""
Apply configuration presets into BacktestWeb user config stored in DB.

Usage examples (from repo root):
    .venv/Scripts/python.exe scripts/apply_config_preset.py --preset rsi_minimo --user admin
    .venv/Scripts/python.exe scripts/apply_config_preset.py --file preset.json --user admin --replace
    .venv/Scripts/python.exe scripts/apply_config_preset.py --preset rsi_minimo --dry-run
    .venv/Scripts/python.exe scripts/apply_config_preset.py --list-presets
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRESETS_DIR = PROJECT_ROOT / "scripts" / "presets"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.database import Usuario
from trading_engine.core.database_pg import db


PRESETS = {
    "rsi_minimo": {
        "rsi": True,
        "rsi_period": 10,
        "rsi_low_level": 20,
        "rsi_high_level": 70,
        "rsi_strength_threshold": 0,
        "rsi_minimo": True,
        "rsi_ascendente": False,
        "rsi_maximo": False,
        "rsi_descendente": False,
        "ema_slow_ascendente": True,
        "stoploss_percentage_below_close": 0.10,
        "breakeven_enabled": True,
        "breakeven_trigger_pct": 0.03,
    }
}


def _load_json_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Preset file must contain a JSON object at root.")
    return data


def _discover_file_presets() -> list[str]:
    if not PRESETS_DIR.exists():
        return []
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json") if p.is_file())


def _load_named_preset(name: str) -> dict:
    # 1) Prefer file-based preset library under scripts/presets/
    file_path = PRESETS_DIR / f"{name}.json"
    if file_path.exists():
        return _load_json_file(file_path)

    # 2) Backward-compatible fallback to embedded presets
    if name in PRESETS:
        return PRESETS[name]

    available = sorted(set(_discover_file_presets()) | set(PRESETS.keys()))
    raise ValueError(f"Unknown preset '{name}'. Available: {', '.join(available) if available else '(none)'}")


def _normalize_value(value):
    if isinstance(value, bool):
        return "True" if value else "False"
    return value


def _normalize_payload(payload: dict) -> dict:
    return {str(k): _normalize_value(v) for k, v in payload.items()}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply config preset into Usuario.config_actual")
    source_group = parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument("--preset", help="Preset name (looks for scripts/presets/<name>.json first)")
    source_group.add_argument("--file", type=Path, help="JSON file containing a config block")
    parser.add_argument("--list-presets", action="store_true", help="List available preset names and exit")

    parser.add_argument("--user", default="admin", help="Target username (default: admin)")
    parser.add_argument("--replace", action="store_true", help="Replace existing config instead of merge")
    parser.add_argument("--dry-run", action="store_true", help="Show result without writing DB")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.list_presets:
        file_presets = _discover_file_presets()
        embedded = sorted(PRESETS.keys())
        print("Available presets from scripts/presets:")
        if file_presets:
            for p in file_presets:
                print(f"  - {p}")
        else:
            print("  (none)")

        print("Embedded fallback presets:")
        for p in embedded:
            print(f"  - {p}")
        return 0

    if not args.preset and not args.file:
        print("ERROR: provide --preset <name> or --file <path>, or use --list-presets")
        return 2

    if args.preset:
        try:
            incoming = _load_named_preset(args.preset)
        except ValueError as e:
            print(f"ERROR: {e}")
            return 2
    else:
        if not args.file.exists():
            print(f"ERROR: file not found: {args.file}")
            return 2
        incoming = _load_json_file(args.file)

    incoming = _normalize_payload(incoming)

    app = create_app(user_mode=args.user)
    with app.app_context():
        user = Usuario.query.filter_by(username=args.user).first()
        if not user:
            print(f"ERROR: user '{args.user}' not found in table usuarios")
            return 3

        current = {}
        if user.config_actual:
            try:
                current = json.loads(user.config_actual) if isinstance(user.config_actual, str) else dict(user.config_actual)
            except Exception:
                current = {}

        result = dict(incoming) if args.replace else {**current, **incoming}

        if args.dry_run:
            print("DRY RUN - resulting config block:")
            if args.pretty:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(result, ensure_ascii=False))
            return 0

        user.config_actual = json.dumps(result, ensure_ascii=False)
        db.session.commit()

        print(
            f"OK: config applied to user='{args.user}' "
            f"mode={'replace' if args.replace else 'merge'} keys={len(incoming)}"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
