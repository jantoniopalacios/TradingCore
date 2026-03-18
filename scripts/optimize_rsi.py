#!/usr/bin/env python3
"""
Optimiza configuraciones RSI con backtesting.Backtest.optimize(),
manteniendo fijo el baseline acordado:

- EMA lenta ascendente (filtro AND) con periodo configurable (default 200)
- Trailing stop base fijo (default 10%)
- Break-even fijo (default 3%)
- Sin MACD/Stoch/BB/Swing

Modos de optimizacion:
1) gate   : RSI como filtro global AND de fuerza (rsi_strength_threshold)
2) minimo : RSI como senyal OR de giro desde sobreventa (rsi_minimo + rsi_low_level)

Ejemplo:
  python scripts/optimize_rsi.py --symbols ZTS SAN.MC --mode gate
  python scripts/optimize_rsi.py --symbols ZTS SAN.MC --mode minimo
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import pandas as pd
from backtesting import Backtest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.BacktestWeb.estrategia_system import System


def _load_ohlcv(symbol: str, interval: str, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    csv_path = PROJECT_ROOT / "Data_files" / f"{symbol}_{interval}_MAX.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {csv_path}")

    df = pd.read_csv(csv_path)
    date_col = next((c for c in ["Date", "date", "Fecha", "fecha", "Datetime", "datetime"] if c in df.columns), None)
    if not date_col:
        raise ValueError("No se encontro columna de fecha en CSV")

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


def _set_fixed_baseline(ema_slow: int, stop: float, breakeven: float) -> None:
    # EMA
    System.ema_cruce_signal = False
    System.ema_fast_period = 5
    System.ema_slow_period = int(ema_slow)
    System.ema_slow_minimo = False
    System.ema_slow_ascendente = True
    System.ema_slow_maximo = False
    System.ema_slow_descendente = False

    # Stops
    System.stoploss_percentage_below_close = float(stop)
    System.stoploss_swing_enabled = False
    System.breakeven_enabled = True
    System.breakeven_trigger_pct = float(breakeven)

    # Otros indicadores OFF
    System.macd = False
    System.stoch_fast = False
    System.stoch_mid = False
    System.stoch_slow = False
    System.bb_active = False

    # Defaults RSI (los parametros optimizados sobreescriben estos)
    System.rsi = True
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


def _fmt(v, d=2):
    try:
        return round(float(v), d)
    except Exception:
        return None


def _export_symbol_csv(
    output_dir: Path,
    symbol: str,
    mode: str,
    maximize: str,
    top: pd.Series,
    best_stats,
    interval: str,
    start: str,
    end: str,
    ema_slow: int,
    stop: float,
    breakeven: float,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1) Best summary (1 fila)
    best_row = {
        "timestamp": ts,
        "symbol": symbol,
        "mode": mode,
        "maximize": maximize,
        "interval": interval,
        "start": start,
        "end": end,
        "ema_slow": ema_slow,
        "stop": stop,
        "breakeven": breakeven,
        "best_return_pct": _fmt(best_stats.get("Return [%]")),
        "best_winrate_pct": _fmt(best_stats.get("Win Rate [%]")),
        "best_maxdd_pct": _fmt(best_stats.get("Max. Drawdown [%]")),
        "best_sharpe": _fmt(best_stats.get("Sharpe Ratio"), 3),
        "best_trades": _fmt(best_stats.get("# Trades"), 0),
        "best_rsi_period": getattr(best_stats._strategy, "rsi_period", None),
        "best_rsi_low_level": getattr(best_stats._strategy, "rsi_low_level", None),
        "best_rsi_strength_threshold": getattr(best_stats._strategy, "rsi_strength_threshold", None),
    }
    best_df = pd.DataFrame([best_row])
    best_path = output_dir / f"optimize_rsi_best_{symbol}_{mode}_{ts}.csv"
    best_df.to_csv(best_path, index=False)

    # 2) Top N combinaciones
    top_rows = []
    for rank, (idx, score) in enumerate(top.items(), start=1):
        row = {
            "rank": rank,
            "symbol": symbol,
            "mode": mode,
            "maximize": maximize,
            "score": _fmt(score, 6),
        }
        if isinstance(idx, tuple):
            for name, val in zip(top.index.names, idx):
                row[name] = val
        else:
            row[top.index.names[0]] = idx
        top_rows.append(row)

    top_df = pd.DataFrame(top_rows)
    top_path = output_dir / f"optimize_rsi_top_{symbol}_{mode}_{ts}.csv"
    top_df.to_csv(top_path, index=False)
    return best_path, top_path


def run_optimize(
    symbols: list[str],
    mode: str,
    interval: str,
    start: str,
    end: str,
    ema_slow: int,
    stop: float,
    breakeven: float,
    maximize: str,
    topn: int,
    out_dir: str,
    export_csv: bool,
) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")

    print("=" * 96)
    print("OPTIMIZE RSI (backtesting.Backtest.optimize)")
    print(f"Fixed baseline: EMA{ema_slow} ascendente + stop={stop:.0%} + breakeven={breakeven:.0%}")
    print(f"Mode={mode} | Maximize='{maximize}' | Interval={interval} | Range={start} -> {end}")
    if export_csv:
        print(f"CSV export: ON -> {out_dir}")
    else:
        print("CSV export: OFF")
    print("=" * 96)

    for symbol in symbols:
        data = _load_ohlcv(symbol, interval, start, end)
        _set_fixed_baseline(ema_slow=ema_slow, stop=stop, breakeven=breakeven)
        System.ticker = symbol

        # Config fija por modo
        if mode == "gate":
            # Filtro de fuerza AND
            System.rsi_minimo = False
            System.rsi_ascendente = False
            # Parametros a optimizar: rsi_period + rsi_strength_threshold
            params = {
                "rsi_period": [10, 12, 14, 16, 18, 20],
                "rsi_strength_threshold": [30, 35, 40, 45, 50],
            }
        else:
            # Giro desde sobreventa OR
            System.rsi_strength_threshold = 0
            System.rsi_ascendente = False
            System.rsi_minimo = True
            # Parametros a optimizar: rsi_period + rsi_low_level
            params = {
                "rsi_period": [10, 12, 14, 16, 18, 20],
                "rsi_low_level": [20, 25, 30, 35, 40],
            }

        bt = Backtest(
            data,
            System,
            cash=10000,
            commission=0.0,
            trade_on_close=True,
            finalize_trades=True,
        )

        best_stats, heatmap = bt.optimize(
            maximize=maximize,
            return_heatmap=True,
            **params,
        )

        print("\n" + "-" * 96)
        print(f"SYMBOL: {symbol}")
        print("-" * 96)

        # Mejor resultado completo
        print("Mejor combinacion:")
        if mode == "gate":
            print(f"  rsi_period={best_stats._strategy.rsi_period}, rsi_strength_threshold={best_stats._strategy.rsi_strength_threshold}")
        else:
            print(f"  rsi_period={best_stats._strategy.rsi_period}, rsi_low_level={best_stats._strategy.rsi_low_level}")

        print(
            "  Return={ret}%  WinRate={wr}%  MaxDD={dd}%  Sharpe={sh}  #Trades={tr}".format(
                ret=_fmt(best_stats.get("Return [%]")),
                wr=_fmt(best_stats.get("Win Rate [%]")),
                dd=_fmt(best_stats.get("Max. Drawdown [%]")),
                sh=_fmt(best_stats.get("Sharpe Ratio"), 3),
                tr=_fmt(best_stats.get("# Trades"), 0),
            )
        )

        # Top N de combinaciones segun la metrica objetivo
        print(f"\nTop {topn} combinaciones por {maximize}:")
        top = heatmap.sort_values(ascending=False).head(topn)
        for idx, score in top.items():
            if isinstance(idx, tuple):
                parts = [f"{name}={val}" for name, val in zip(top.index.names, idx)]
                ptxt = ", ".join(parts)
            else:
                ptxt = f"{top.index.names[0]}={idx}"
            print(f"  {ptxt} -> {maximize}={_fmt(score)}")

        if export_csv:
            best_path, top_path = _export_symbol_csv(
                output_dir=PROJECT_ROOT / out_dir,
                symbol=symbol,
                mode=mode,
                maximize=maximize,
                top=top,
                best_stats=best_stats,
                interval=interval,
                start=start,
                end=end,
                ema_slow=ema_slow,
                stop=stop,
                breakeven=breakeven,
            )
            print(f"\nCSV best: {best_path}")
            print(f"CSV top : {top_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimiza RSI con bt.optimize() sobre baseline fijo.")
    parser.add_argument("--symbols", nargs="+", default=["ZTS", "SAN.MC"])
    parser.add_argument("--mode", choices=["gate", "minimo"], default="gate")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-03-16")
    parser.add_argument("--ema-slow", type=int, default=200)
    parser.add_argument("--stop", type=float, default=0.10)
    parser.add_argument("--breakeven", type=float, default=0.03)
    parser.add_argument("--maximize", default="Return [%]")
    parser.add_argument("--topn", type=int, default=10)
    parser.add_argument("--out-dir", default="Backtesting/Run_Results/optimizations")
    parser.add_argument("--no-export-csv", action="store_true", help="No genera CSV de salida")
    args = parser.parse_args()

    run_optimize(
        symbols=args.symbols,
        mode=args.mode,
        interval=args.interval,
        start=args.start,
        end=args.end,
        ema_slow=args.ema_slow,
        stop=args.stop,
        breakeven=args.breakeven,
        maximize=args.maximize,
        topn=args.topn,
        out_dir=args.out_dir,
        export_csv=not args.no_export_csv,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
