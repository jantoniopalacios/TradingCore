#!/usr/bin/env python3
"""
Standalone stop-combinations auditor.

Purpose:
- Validate stop interaction scenarios without touching app code.
- Reuse production strategy + runner as a black box.
- Flag obvious source-leak bugs in stop reason labeling.

Scenarios included:
1) trailing_base          -> only TrailingBase expected
2) breakeven_only         -> TrailingBase/BreakEven possible
3) swing_only             -> TrailingBase/Swing possible
4) breakeven_and_swing    -> TrailingBase/BreakEven/Swing possible
5) rsi_trailing_guard_off -> RSI trailing params filled but RSI disabled; RSI sources forbidden
6) rsi_trailing_on        -> RSI trailing enabled; RSI sources allowed
"""

from __future__ import annotations

import argparse
import copy
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
from scenarios.BacktestWeb.estrategia_system import System


@dataclass
class ScenarioResult:
    name: str
    trades: int
    stop_sales: int
    ret_pct: float
    source_counts: Dict[str, int]
    findings: List[str]


def _parse_decimal(value: str) -> float:
    return float(value.strip().replace("%", "").replace(",", "."))


def _load_ohlcv(symbol: str, interval: str, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    csv_path = PROJECT_ROOT / "Data_files" / f"{symbol}_{interval}_MAX.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    date_col = next((c for c in ["Date", "date", "Fecha", "fecha", "Datetime", "datetime"] if c in df.columns), None)
    if not date_col:
        raise ValueError("No datetime column found in CSV")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing OHLCV columns: {missing}")

    out = df[required].copy()
    if start:
        out = out[out.index >= pd.to_datetime(start)]
    if end:
        out = out[out.index <= pd.to_datetime(end)]
    return out.dropna()


def _set_system_attr(attrs: Dict[str, object]) -> None:
    for k, v in attrs.items():
        setattr(System, k, v)


def _base_config(ema_slow: int) -> Dict[str, object]:
    return {
        # B&H context
        "ema_cruce_signal": False,
        "ema_fast_period": 5,
        "ema_slow_period": int(ema_slow),
        "ema_slow_minimo": False,
        "ema_slow_ascendente": False,
        "ema_slow_maximo": False,
        "ema_slow_descendente": False,
        # Indicators off
        "rsi": False,
        "rsi_period": 14,
        "rsi_low_level": 30,
        "rsi_high_level": 70,
        "rsi_strength_threshold": 50,
        "rsi_minimo": False,
        "rsi_ascendente": False,
        "rsi_maximo": False,
        "rsi_descendente": False,
        "rsi_trailing_limit": None,
        "trailing_pct_below": None,
        "trailing_pct_above": None,
        "macd": False,
        "stoch_fast": False,
        "stoch_mid": False,
        "stoch_slow": False,
        "bb_active": False,
        # Stops extra
        "stoploss_swing_enabled": False,
        "stoploss_swing_lookback": 10,
        "stoploss_swing_buffer": 1.0,
        "breakeven_enabled": False,
        "breakeven_trigger_pct": None,
    }


def _extract_stop_source(desc: str) -> Optional[str]:
    m = re.search(r"StopLoss\s*\(([^)]+)\)", str(desc))
    return m.group(1).strip() if m else None


def _run_scenario(
    scenario_name: str,
    data: pd.DataFrame,
    symbol: str,
    stoploss: float,
    base_cfg: Dict[str, object],
    overrides: Dict[str, object],
    logger: logging.Logger,
) -> ScenarioResult:
    cfg = copy.deepcopy(base_cfg)
    cfg.update(overrides)
    _set_system_attr(cfg)

    stats, trades_log, _ = run_backtest_for_symbol(
        data_clean=data,
        strategy_class=System,
        symbol=symbol,
        cash=10000,
        commission=0.0,
        stoploss_percentage=stoploss,
        logger=logger,
    )

    trades_df = pd.DataFrame(trades_log)
    if trades_df.empty:
        return ScenarioResult(scenario_name, 0, 0, 0.0, {}, [])

    sales = trades_df[
        (trades_df.get("Tipo", "").astype(str).str.upper() == "VENTA")
        & (trades_df.get("Descripcion", "").astype(str).str.contains("StopLoss", case=False, na=False))
    ].copy()

    source_counts: Dict[str, int] = {}
    for d in sales.get("Descripcion", []):
        src = _extract_stop_source(d)
        if src:
            source_counts[src] = source_counts.get(src, 0) + 1

    findings: List[str] = []

    # Guard checks: verify no forbidden source leaks by scenario design.
    if not cfg.get("rsi", False):
        leaked = [s for s in source_counts if s.startswith("TrailingRSI")]
        if leaked:
            findings.append(f"RSI disabled but RSI stop source leaked: {leaked}")

    if not cfg.get("breakeven_enabled", False) and "BreakEven" in source_counts:
        findings.append("BreakEven source appeared while breakeven_enabled=False")

    if not cfg.get("stoploss_swing_enabled", False) and "Swing" in source_counts:
        findings.append("Swing source appeared while stoploss_swing_enabled=False")

    return ScenarioResult(
        name=scenario_name,
        trades=len(trades_df),
        stop_sales=len(sales),
        ret_pct=float(stats.get("Return [%]", 0.0)),
        source_counts=source_counts,
        findings=findings,
    )


def run_audit(symbol: str, interval: str, start: str, end: str, ema_slow: int, stoploss: float) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    logger = logging.getLogger("audit_stops_combo")

    data = _load_ohlcv(symbol, interval, start, end)
    base_cfg = _base_config(ema_slow)

    scenarios: List[Tuple[str, Dict[str, object]]] = [
        ("trailing_base", {}),
        ("breakeven_only", {
            "breakeven_enabled": True,
            "breakeven_trigger_pct": 0.02,
        }),
        ("swing_only", {
            "stoploss_swing_enabled": True,
            "stoploss_swing_lookback": 10,
            "stoploss_swing_buffer": 1.0,
        }),
        ("breakeven_and_swing", {
            "breakeven_enabled": True,
            "breakeven_trigger_pct": 0.02,
            "stoploss_swing_enabled": True,
            "stoploss_swing_lookback": 10,
            "stoploss_swing_buffer": 1.0,
        }),
        ("rsi_trailing_guard_off", {
            "rsi": False,
            "rsi_trailing_limit": 50,
            "trailing_pct_below": 0.03,
            "trailing_pct_above": 0.20,
        }),
        ("rsi_trailing_on", {
            "rsi": True,
            "rsi_period": 14,
            "rsi_low_level": 30,
            "rsi_high_level": 70,
            "rsi_strength_threshold": 50,
            "rsi_trailing_limit": 50,
            "trailing_pct_below": 0.03,
            "trailing_pct_above": 0.20,
        }),
    ]

    print("\n=== STOP COMBINATIONS AUDIT ===")
    print(f"Symbol={symbol} interval={interval} range={start}..{end} ema_slow={ema_slow} stop={stoploss}")

    results: List[ScenarioResult] = []
    for name, overrides in scenarios:
        r = _run_scenario(name, data, symbol, stoploss, base_cfg, overrides, logger)
        results.append(r)

    for r in results:
        print(
            f"- {r.name}: trades={r.trades} stop_sales={r.stop_sales} return={r.ret_pct:.2f}% sources={r.source_counts}"
        )

    all_findings: List[str] = []
    for r in results:
        for f in r.findings:
            all_findings.append(f"{r.name}: {f}")

    if not all_findings:
        print("\nNo source-leak issues detected in stop combination scenarios.")
        return 0

    print("\nFindings:")
    for f in all_findings:
        print(f"- [error] {f}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit stop combinations without changing application code.")
    parser.add_argument("--symbol", default="ZTS")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-03-16")
    parser.add_argument("--ema-slow", type=int, default=200)
    parser.add_argument("--stop", default="0.10", help="Trailing stop value. Accepts 0.10 or 0,10")
    args = parser.parse_args()

    stoploss = _parse_decimal(str(args.stop))
    return run_audit(args.symbol, args.interval, args.start, args.end, args.ema_slow, stoploss)


if __name__ == "__main__":
    raise SystemExit(main())
