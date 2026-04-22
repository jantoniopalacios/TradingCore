#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.database import Trade
from trading_engine.core.database_pg import db


def _extract_stop_source(description: str) -> str | None:
    match = re.search(r"StopLoss\s*\(([^)]+)\)", description, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _infer_signal_context(description: str) -> dict | None:
    if not description:
        return None

    text = description.strip()
    lowered = text.lower()

    trigger_candidates = []
    indicator_context = {}

    indicator_patterns = [
        ("EMA", ["ema"]),
        ("RSI", ["rsi"]),
        ("MACD", ["macd"]),
        ("Stoch", ["stoch", "stochastic"]),
        ("BB", ["bb", "bollinger"]),
        ("Volume", ["volume", "volumen"]),
        ("ATR", ["atr"]),
        ("MoS", ["mos", "margen de seguridad"]),
    ]

    for indicator_name, keywords in indicator_patterns:
        if any(keyword in lowered for keyword in keywords):
            trigger_candidates.append(indicator_name)
            indicator_context[indicator_name] = {
                "razon": text,
                "inferido": True,
            }

    trigger = trigger_candidates[0] if trigger_candidates else None

    if "stoploss" in lowered:
        stop_source = _extract_stop_source(text)
        return {
            "trigger": "stop_loss",
            "trigger_candidates": ["stop_loss"],
            "source": "descripcion_backfill",
            "descripcion_original": text,
            "inferred_from_description": True,
            "stop_source": stop_source,
            "indicadores": {},
        }

    if not trigger_candidates:
        return {
            "trigger": None,
            "trigger_candidates": [],
            "source": "descripcion_backfill",
            "descripcion_original": text,
            "inferred_from_description": True,
            "indicadores": {},
        }

    return {
        "trigger": trigger,
        "trigger_candidates": trigger_candidates,
        "source": "descripcion_backfill",
        "descripcion_original": text,
        "inferred_from_description": True,
        "indicadores": indicator_context,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rellena signal_context de trades históricos a partir de la descripcion."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica cambios en BD. Sin esta bandera, solo hace dry-run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Número máximo de trades a inspeccionar/actualizar.",
    )
    args = parser.parse_args()

    app = create_app(user_mode="admin")

    with app.app_context():
        query = (
            Trade.query
            .filter((Trade.signal_context.is_(None)) | (Trade.signal_context == ""))
            .order_by(Trade.id.desc())
            .limit(args.limit)
        )
        trades = query.all()

        print(f"Trades candidatos: {len(trades)}")
        if not trades:
            return 0

        updated = 0
        for trade in trades:
            inferred = _infer_signal_context(trade.descripcion or "")
            if inferred is None:
                continue

            print(
                json.dumps(
                    {
                        "trade_id": trade.id,
                        "tipo": trade.tipo,
                        "descripcion": trade.descripcion,
                        "trigger": inferred.get("trigger"),
                        "trigger_candidates": inferred.get("trigger_candidates"),
                    },
                    ensure_ascii=False,
                )
            )

            if args.apply:
                trade.signal_context = json.dumps(inferred, ensure_ascii=False)
                updated += 1

        if args.apply:
            db.session.commit()
            print(f"Actualizados: {updated}")
        else:
            print("Dry-run completado. No se escribieron cambios.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
