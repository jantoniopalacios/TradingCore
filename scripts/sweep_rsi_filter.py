#!/usr/bin/env python3
"""
Barrido de filtros RSI sobre baseline EMA-ascendente + trailing 10% + break-even 3%.

Baseline fijo (sin tocar la aplicacion):
  - EMA lenta 200, filtro AND ascendente (solo compra cuando EMA200 sube)
  - Trailing stop 10% (Close/Close)
  - Break-Even 3% (target_trigger=0.03)
  - Sin indicadores tecnicos adicionales

Escenarios que barre:
  A) baseline        : sin RSI
  B) rsi_gate_XX     : RSI activo, rsi_strength_threshold=XX (filtro AND puro)
                       Solo compra si RSI >= XX en el momento de la senyal
                       Umbrales: 30, 35, 40, 45, 50
  C) rsi_minimo_XX   : RSI activo, rsi_low_level=XX, rsi_minimo=True (senyal OR)
                       Compra cuando RSI gira al alza desde zona de sobreventa (< XX)
                       Umbrales: 25, 30, 35, 40

Metricas por fila: Return [%], Win Rate [%], Max DD [%], Sharpe, Trades, Stop-Sales

Uso:
    python scripts/sweep_rsi_filter.py --symbols ZTS SAN.MC --interval 1d \
        --start 2023-01-01 --end 2026-03-16 --ema-slow 200

Parametros opcionales:
    --stop 0.10          trailing stop (default: 0.10)
    --breakeven 0.03     break-even trigger pct (default: 0.03)
    --rsi-period 14      periodo RSI (default: 14)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
from scenarios.BacktestWeb.estrategia_system import System


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_decimal(value: str) -> float:
    return float(value.strip().replace("%", "").replace(",", "."))


def _load_ohlcv(symbol: str, interval: str, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    csv_path = PROJECT_ROOT / "Data_files" / f"{symbol}_{interval}_MAX.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {csv_path}")
    df = pd.read_csv(csv_path)
    date_col = next(
        (c for c in ["Date", "date", "Fecha", "fecha", "Datetime", "datetime"] if c in df.columns), None
    )
    if not date_col:
        raise ValueError("Columna de fecha no encontrada en CSV")
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV sin columnas OHLCV: {missing}")
    out = df[required].copy()
    if start:
        out = out[out.index >= pd.to_datetime(start)]
    if end:
        out = out[out.index <= pd.to_datetime(end)]
    return out.dropna()


def _reset_system(ema_slow_period: int, stop: float, breakeven_pct: float) -> None:
    """Configura el baseline comun a todos los escenarios."""
    # --- EMA ---
    System.ema_cruce_signal = False
    System.ema_fast_period = 5
    System.ema_slow_period = int(ema_slow_period)
    System.ema_slow_minimo = False
    System.ema_slow_ascendente = True   # filtro AND: solo compra cuando EMA200 sube
    System.ema_slow_maximo = False
    System.ema_slow_descendente = False

    # --- RSI (reset total) ---
    System.rsi = False
    System.rsi_period = 14
    System.rsi_low_level = 30
    System.rsi_high_level = 70
    System.rsi_strength_threshold = 0
    System.rsi_minimo = False
    System.rsi_maximo = False
    System.rsi_ascendente = False
    System.rsi_descendente = False
    System.rsi_trailing_limit = None
    System.trailing_pct_below = None
    System.trailing_pct_above = None

    # --- Resto de indicadores OFF ---
    System.macd = False
    System.stoch_fast = False
    System.stoch_mid = False
    System.stoch_slow = False
    System.bb_active = False

    # --- Stops ---
    System.stoploss_swing_enabled = False
    System.breakeven_enabled = True
    System.breakeven_trigger_pct = breakeven_pct


def _extract_kpis(stats: dict, trades_log: list) -> dict:
    def _f(key, decimals=2):
        try:
            return round(float(stats.get(key, 0) or 0), decimals)
        except Exception:
            return None

    n_compras = sum(1 for t in trades_log if str(t.get("Tipo", "")).upper() == "COMPRA")
    n_stop = sum(
        1 for t in trades_log
        if str(t.get("Tipo", "")).upper() == "VENTA"
        and "StopLoss" in str(t.get("Descripcion", ""))
    )
    return {
        "Return [%]":   _f("Return [%]"),
        "WinRate [%]":  _f("Win Rate [%]"),
        "MaxDD [%]":    _f("Max. Drawdown [%]"),
        "Sharpe":       _f("Sharpe Ratio", 3),
        "Trades":       n_compras,
        "StopSales":    n_stop,
    }


def _build_scenarios(rsi_period: int) -> list[dict]:
    """
    Devuelve lista de escenarios. Cada dict tiene:
      name, rsi, rsi_period, rsi_strength_threshold, rsi_low_level, rsi_minimo
    """
    scenarios = []

    # A) Baseline sin RSI
    scenarios.append({
        "name": "baseline",
        "rsi": False,
        "rsi_period": rsi_period,
        "rsi_strength_threshold": 0,
        "rsi_low_level": 30,
        "rsi_high_level": 70,
        "rsi_minimo": False,
        "rsi_ascendente": False,
    })

    # B) RSI gate (filtro AND fuerza): rsi_strength_threshold barre 30..50
    for thr in [30, 35, 40, 45, 50]:
        scenarios.append({
            "name": f"rsi_gate_{thr}",
            "rsi": True,
            "rsi_period": rsi_period,
            "rsi_strength_threshold": thr,
            "rsi_low_level": 30,        # necesario para init del indicador
            "rsi_high_level": 70,
            "rsi_minimo": False,
            "rsi_ascendente": False,
        })

    # C) RSI minimo (senyal OR desde sobreventa): rsi_low_level barre 25..40
    for lvl in [25, 30, 35, 40]:
        scenarios.append({
            "name": f"rsi_minimo_{lvl}",
            "rsi": True,
            "rsi_period": rsi_period,
            "rsi_strength_threshold": 0,  # filtro de fuerza desactivado
            "rsi_low_level": lvl,
            "rsi_high_level": 70,
            "rsi_minimo": True,
            "rsi_ascendente": False,
        })

    return scenarios


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def run_sweep(
    symbols: list[str],
    interval: str,
    start: str,
    end: str,
    ema_slow_period: int,
    stop: float,
    breakeven_pct: float,
    rsi_period: int,
) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
    logger = logging.getLogger("sweep_rsi")

    scenarios = _build_scenarios(rsi_period)

    all_rows = []

    for symbol in symbols:
        print(f"\nCargando datos: {symbol} {interval} {start} -> {end}")
        data = _load_ohlcv(symbol, interval, start, end)

        for sc in scenarios:
            # Inyectar configuracion en System (sin tocar la app)
            _reset_system(ema_slow_period, stop, breakeven_pct)
            System.rsi                  = sc["rsi"]
            System.rsi_period           = sc["rsi_period"]
            System.rsi_strength_threshold = sc["rsi_strength_threshold"]
            System.rsi_low_level        = sc["rsi_low_level"]
            System.rsi_high_level       = sc["rsi_high_level"]
            System.rsi_minimo           = sc["rsi_minimo"]
            System.rsi_ascendente       = sc["rsi_ascendente"]

            stats, trades_log, _ = run_backtest_for_symbol(
                data_clean=data,
                strategy_class=System,
                symbol=symbol,
                cash=10000,
                commission=0.0,
                stoploss_percentage=stop,
                logger=logger,
            )

            kpis = _extract_kpis(stats, trades_log)
            all_rows.append({"Symbol": symbol, "Scenario": sc["name"], **kpis})

    # ---------------------------------------------------------------------------
    # Presentacion
    # ---------------------------------------------------------------------------
    df = pd.DataFrame(all_rows)

    col_w = {
        "Symbol":     8,
        "Scenario":   18,
        "Return [%]": 12,
        "WinRate [%]":12,
        "MaxDD [%]":  10,
        "Sharpe":     8,
        "Trades":     7,
        "StopSales":  10,
    }

    print("\n" + "=" * 95)
    print(f"SWEEP RSI  --  baseline: EMA{ema_slow_period}-asc + stop={stop:.0%} + breakeven={breakeven_pct:.0%}")
    print(f"Intervalo: {interval}  Rango: {start} -> {end}  RSI period: {rsi_period}")
    print("=" * 95)
    print(
        "Grupos: [baseline]  [rsi_gate: AND-filter fuerza]  [rsi_minimo: OR-signal sobreventa]"
    )
    header = "  ".join(k.ljust(v) for k, v in col_w.items())
    print("\n" + header)
    print("-" * len(header))

    prev_sym = None
    prev_group = None

    def _group(name: str) -> str:
        if name == "baseline":
            return "A"
        if name.startswith("rsi_gate"):
            return "B"
        return "C"

    for _, r in df.iterrows():
        sym = r["Symbol"]
        grp = _group(r["Scenario"])
        if prev_sym and sym != prev_sym:
            print()
        if prev_group and grp != prev_group and sym == prev_sym:
            print()
        prev_sym = sym
        prev_group = grp

        def _fmt(col, w):
            v = r.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return "N/A".ljust(w)
            if isinstance(v, float):
                return f"{v:.2f}".ljust(w)
            return str(v).ljust(w)

        print("  ".join(_fmt(c, w) for c, w in col_w.items()))

    # -----------------------------------------------------------------------
    # Delta vs baseline por simbolo
    # -----------------------------------------------------------------------
    print("\n" + "=" * 95)
    print("DELTA vs baseline  (escenario - baseline, por simbolo)")
    print("=" * 95)
    num_cols = ["Return [%]", "WinRate [%]", "MaxDD [%]", "Sharpe", "Trades", "StopSales"]

    for symbol in symbols:
        sub = df[df["Symbol"] == symbol].copy()
        base = sub[sub["Scenario"] == "baseline"].iloc[0]
        rest = sub[sub["Scenario"] != "baseline"].copy()

        print(f"\n  {symbol}")
        dheader = "  " + "Scenario".ljust(18) + "  " + "  ".join(f"D_{c[:6]}".ljust(10) for c in num_cols)
        print(dheader)
        print("  " + "-" * (len(dheader) - 2))

        for _, r in rest.iterrows():
            parts = ["  " + r["Scenario"].ljust(18)]
            for c in num_cols:
                try:
                    delta = float(r[c]) - float(base[c])
                    parts.append(f"{delta:+.2f}".ljust(10))
                except Exception:
                    parts.append("N/A".ljust(10))
            print("  ".join(parts))

    print()
    print("Interpretar: D_Return positivo = mejora vs baseline; D_MaxDD negativo = menos drawdown.")
    print("Grupos: A=baseline  B=rsi_gate (AND fuerza, bloquea si RSI<umbral)  C=rsi_minimo (OR sobreventa)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Barrido RSI sobre baseline EMA-asc + trailing 10% + break-even 3%."
    )
    parser.add_argument("--symbols",    nargs="+", default=["ZTS", "SAN.MC"])
    parser.add_argument("--interval",   default="1d")
    parser.add_argument("--start",      default="2023-01-01")
    parser.add_argument("--end",        default="2026-03-16")
    parser.add_argument("--ema-slow",   type=int,   default=200)
    parser.add_argument("--stop",       type=float, default=0.10)
    parser.add_argument("--breakeven",  type=float, default=0.03)
    parser.add_argument("--rsi-period", type=int,   default=14)
    args = parser.parse_args()

    run_sweep(
        symbols=args.symbols,
        interval=args.interval,
        start=args.start,
        end=args.end,
        ema_slow_period=args.ema_slow,
        stop=args.stop,
        breakeven_pct=args.breakeven,
        rsi_period=args.rsi_period,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
