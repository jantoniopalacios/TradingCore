#!/usr/bin/env python3
"""
TradingCore - Diagnostico comparativo de proveedores fundamentales.

Objetivo
--------
Comparar, sin modificar el flujo productivo, la cobertura de EPS trimestral y
fechas de publicacion de:

1. Yahoo Finance / yfinance
2. Alpha Vantage / endpoint EARNINGS
3. Cache CSV actual de TradingCore (opcional, solo lectura)

El script NO escribe en Data_Files/Fundamentals ni en PostgreSQL.

Uso recomendado (PowerShell)
----------------------------
$env:ALPHA_VANTAGE_KEY="TU_CLAVE"
python .\scripts\diagnostics\compare_fundamental_providers.py

Opcional:
python .\scripts\diagnostics\compare_fundamental_providers.py `
    --symbols AAPL MSFT ZTS SAN.MC `
    --output .\Backtesting\diagnostics\fundamentals_provider_comparison

Notas
-----
- Yahoo no ofrece en una sola tabla el mismo contrato que Alpha Vantage.
  Se extraen por separado:
    * EPS diluido trimestral del income statement.
    * fechas de earnings y Reported EPS de get_earnings_dates().
- La asociacion Yahoo entre fecha fiscal y fecha de publicacion se realiza como
  diagnostico heuristico: se asigna el primer evento de earnings posterior a
  cada cierre fiscal dentro de una ventana configurable. NO debe usarse en
  produccion sin validacion.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import yfinance as yf


DEFAULT_SYMBOLS = ["AAPL", "MSFT", "ZTS", "SAN.MC"]
DEFAULT_EARNINGS_LIMIT = 100
DEFAULT_MATCH_WINDOW_DAYS = 120
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


def _safe_timestamp(value) -> pd.Timestamp:
    try:
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return pd.NaT
        ts = pd.Timestamp(ts)
        if ts.tzinfo is not None:
            ts = ts.tz_convert(None)
        return ts
    except Exception:
        return pd.NaT


def _safe_float(value):
    try:
        if value is None:
            return None
        if isinstance(value, str) and value.strip().lower() in {"", "none", "null", "nan"}:
            return None
        result = float(value)
        return result if pd.notna(result) else None
    except (TypeError, ValueError):
        return None


def _pick_row(df: pd.DataFrame, candidates: list[str]) -> Optional[pd.Series]:
    if df is None or df.empty:
        return None

    normalized = {str(idx).strip().lower(): idx for idx in df.index}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in normalized:
            return df.loc[normalized[key]]
    return None


def fetch_yahoo(symbol: str, earnings_limit: int) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    warnings: list[str] = []
    ticker = yf.Ticker(symbol)

    fiscal_rows = []
    try:
        stmt = ticker.get_income_stmt(freq="quarterly", pretty=True)
        if stmt is None or stmt.empty:
            warnings.append("Yahoo quarterly income statement vacio.")
        else:
            diluted = _pick_row(stmt, ["Diluted EPS", "DilutedEPS", "Diluted Eps"])
            if diluted is None:
                warnings.append("Yahoo no expone fila Diluted EPS en quarterly income statement.")
            else:
                for fiscal_col, eps_value in diluted.items():
                    fiscal_date = _safe_timestamp(fiscal_col)
                    eps = _safe_float(eps_value)
                    if pd.notna(fiscal_date) and eps is not None:
                        fiscal_rows.append({
                            "symbol": symbol,
                            "provider": "yahoo",
                            "fiscal_date": fiscal_date.normalize(),
                            "reported_date": pd.NaT,
                            "eps": eps,
                            "date_source": "quarterly_income_stmt",
                        })
    except Exception as exc:
        warnings.append(f"Error Yahoo quarterly income statement: {exc}")

    fiscal_df = pd.DataFrame(fiscal_rows)
    if not fiscal_df.empty:
        fiscal_df = fiscal_df.drop_duplicates(
            subset=["symbol", "fiscal_date"], keep="first"
        ).sort_values("fiscal_date").reset_index(drop=True)

    event_rows = []
    try:
        earnings_dates = ticker.get_earnings_dates(limit=earnings_limit)
        if earnings_dates is None or earnings_dates.empty:
            warnings.append("Yahoo earnings dates vacio.")
        else:
            tmp = earnings_dates.copy().reset_index()
            date_col = tmp.columns[0]

            reported_col = None
            for candidate in ["Reported EPS", "ReportedEPS"]:
                if candidate in tmp.columns:
                    reported_col = candidate
                    break

            for _, row in tmp.iterrows():
                reported_date = _safe_timestamp(row.get(date_col))
                eps = _safe_float(row.get(reported_col)) if reported_col else None
                if pd.notna(reported_date):
                    event_rows.append({
                        "symbol": symbol,
                        "provider": "yahoo",
                        "reported_date": reported_date,
                        "reported_eps": eps,
                        "date_source": "get_earnings_dates",
                    })

            if reported_col is None:
                warnings.append("Yahoo earnings dates no contiene columna Reported EPS.")
    except Exception as exc:
        warnings.append(f"Error Yahoo earnings dates: {exc}")

    events_df = pd.DataFrame(event_rows)
    if not events_df.empty:
        events_df = events_df.drop_duplicates(
            subset=["symbol", "reported_date"], keep="first"
        ).sort_values("reported_date").reset_index(drop=True)

    return fiscal_df, events_df, warnings


def match_yahoo_fiscal_to_reported(
    fiscal_df: pd.DataFrame,
    events_df: pd.DataFrame,
    max_days: int,
) -> pd.DataFrame:
    if fiscal_df.empty:
        return fiscal_df.copy()

    out = fiscal_df.copy()
    out["matched_reported_date"] = pd.NaT
    out["matched_reported_eps"] = pd.NA
    out["match_delay_days"] = pd.NA
    out["match_quality"] = "unmatched"

    if events_df.empty:
        return out

    events = events_df.sort_values("reported_date").copy()

    for idx, row in out.iterrows():
        fiscal_date = row["fiscal_date"]
        candidates = events[
            (events["reported_date"] >= fiscal_date)
            & (events["reported_date"] <= fiscal_date + pd.Timedelta(days=max_days))
        ]

        if candidates.empty:
            continue

        event = candidates.iloc[0]
        delay = (event["reported_date"].normalize() - fiscal_date.normalize()).days

        out.at[idx, "matched_reported_date"] = event["reported_date"]
        out.at[idx, "matched_reported_eps"] = event["reported_eps"]
        out.at[idx, "match_delay_days"] = delay
        out.at[idx, "match_quality"] = "heuristic_next_event"

    return out


def fetch_alpha_vantage(
    symbol: str,
    api_key: str,
    timeout: int = 30,
) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []

    if not api_key:
        warnings.append("ALPHA_VANTAGE_KEY no configurada; Alpha Vantage omitido.")
        return pd.DataFrame(), warnings

    try:
        response = requests.get(
            ALPHA_VANTAGE_URL,
            params={
                "function": "EARNINGS",
                "symbol": symbol,
                "apikey": api_key,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        warnings.append(f"Error HTTP/JSON Alpha Vantage: {exc}")
        return pd.DataFrame(), warnings

    if "Note" in payload:
        warnings.append(f"Alpha Vantage rate limit: {payload.get('Note')}")
        return pd.DataFrame(), warnings

    if "Information" in payload:
        warnings.append(f"Alpha Vantage info: {payload.get('Information')}")
        return pd.DataFrame(), warnings

    if "Error Message" in payload:
        warnings.append(f"Alpha Vantage error: {payload.get('Error Message')}")
        return pd.DataFrame(), warnings

    quarterly = payload.get("quarterlyEarnings")
    if not quarterly:
        warnings.append("Alpha Vantage no devolvio quarterlyEarnings.")
        return pd.DataFrame(), warnings

    rows = []
    for item in quarterly:
        fiscal_date = _safe_timestamp(item.get("fiscalDateEnding"))
        reported_date = _safe_timestamp(item.get("reportedDate"))
        reported_eps = _safe_float(item.get("reportedEPS"))

        if pd.isna(fiscal_date):
            continue

        rows.append({
            "symbol": symbol,
            "provider": "alpha_vantage",
            "fiscal_date": fiscal_date.normalize(),
            "reported_date": reported_date,
            "eps": reported_eps,
            "estimated_eps": _safe_float(item.get("estimatedEPS")),
            "surprise": _safe_float(item.get("surprise")),
            "surprise_percentage": _safe_float(item.get("surprisePercentage")),
            "date_source": "EARNINGS",
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(
            subset=["symbol", "fiscal_date"], keep="first"
        ).sort_values("fiscal_date").reset_index(drop=True)
    return df, warnings


def load_tradingcore_cache(
    symbol: str,
    fundamentals_path: Path,
) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    files = sorted(fundamentals_path.glob(f"Q?_{symbol}.csv"))

    if not files:
        return pd.DataFrame(), [f"Sin cache TradingCore para {symbol}."]

    rows = []
    for path in files:
        try:
            df = pd.read_csv(path, sep=";")
        except Exception as exc:
            warnings.append(f"No se pudo leer {path.name}: {exc}")
            continue

        if "fiscalDateEnding" not in df.columns:
            warnings.append(f"{path.name}: falta fiscalDateEnding.")
            continue

        eps_col = None
        for candidate in ["Diluted EPS", "reportedEPS"]:
            if candidate in df.columns:
                eps_col = candidate
                break

        if eps_col is None:
            warnings.append(f"{path.name}: falta Diluted EPS/reportedEPS.")
            continue

        for _, row in df.iterrows():
            fiscal_date = _safe_timestamp(row.get("fiscalDateEnding"))
            eps = _safe_float(row.get(eps_col))
            if pd.notna(fiscal_date) and eps is not None:
                rows.append({
                    "symbol": symbol,
                    "provider": "tradingcore_cache",
                    "cache_file": path.name,
                    "fiscal_date": fiscal_date.normalize(),
                    "eps": eps,
                })

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.drop_duplicates(
            subset=["symbol", "fiscal_date"], keep="last"
        ).sort_values("fiscal_date").reset_index(drop=True)
    return result, warnings


def compare_eps(
    symbol: str,
    yahoo_fiscal: pd.DataFrame,
    alpha_df: pd.DataFrame,
    cache_df: pd.DataFrame,
) -> pd.DataFrame:
    frames = []

    if not yahoo_fiscal.empty:
        frames.append(
            yahoo_fiscal[["fiscal_date", "eps"]]
            .rename(columns={"eps": "eps_yahoo"})
            .set_index("fiscal_date")
        )

    if not alpha_df.empty:
        frames.append(
            alpha_df[["fiscal_date", "eps", "reported_date"]]
            .rename(columns={
                "eps": "eps_alpha_vantage",
                "reported_date": "reported_date_alpha_vantage",
            })
            .set_index("fiscal_date")
        )

    if not cache_df.empty:
        frames.append(
            cache_df[["fiscal_date", "eps"]]
            .rename(columns={"eps": "eps_tradingcore_cache"})
            .set_index("fiscal_date")
        )

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, axis=1).sort_index().reset_index()
    combined.insert(0, "symbol", symbol)

    if {"eps_yahoo", "eps_alpha_vantage"}.issubset(combined.columns):
        combined["eps_diff_yahoo_vs_av"] = (
            combined["eps_yahoo"] - combined["eps_alpha_vantage"]
        )
        combined["eps_match_yahoo_vs_av"] = (
            combined["eps_diff_yahoo_vs_av"].abs() <= 0.01
        )

    if {"eps_tradingcore_cache", "eps_alpha_vantage"}.issubset(combined.columns):
        combined["eps_diff_cache_vs_av"] = (
            combined["eps_tradingcore_cache"] - combined["eps_alpha_vantage"]
        )
        combined["eps_match_cache_vs_av"] = (
            combined["eps_diff_cache_vs_av"].abs() <= 0.01
        )

    return combined


def summarize_provider(
    symbol: str,
    provider: str,
    df: pd.DataFrame,
    fiscal_col: str = "fiscal_date",
    reported_col: str = "reported_date",
) -> dict:
    result = {
        "symbol": symbol,
        "provider": provider,
        "rows": 0,
        "first_fiscal_date": None,
        "last_fiscal_date": None,
        "first_reported_date": None,
        "last_reported_date": None,
        "eps_non_null": 0,
    }

    if df is None or df.empty:
        return result

    result["rows"] = len(df)

    if fiscal_col in df.columns:
        fiscal = pd.to_datetime(df[fiscal_col], errors="coerce").dropna()
        if not fiscal.empty:
            result["first_fiscal_date"] = fiscal.min().date().isoformat()
            result["last_fiscal_date"] = fiscal.max().date().isoformat()

    if reported_col in df.columns:
        reported = pd.to_datetime(df[reported_col], errors="coerce").dropna()
        if not reported.empty:
            result["first_reported_date"] = reported.min().date().isoformat()
            result["last_reported_date"] = reported.max().date().isoformat()

    for eps_col in ["eps", "reported_eps"]:
        if eps_col in df.columns:
            result["eps_non_null"] = int(
                pd.to_numeric(df[eps_col], errors="coerce").notna().sum()
            )
            break

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compara fundamentales Yahoo, Alpha Vantage y cache actual de TradingCore."
        )
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help="Tickers a comparar. Default: AAPL MSFT ZTS SAN.MC",
    )
    parser.add_argument(
        "--output",
        default="Backtesting/diagnostics/fundamentals_provider_comparison",
        help="Directorio de salida.",
    )
    parser.add_argument(
        "--fundamentals-path",
        default="Data_Files/Fundamentals",
        help="Cache actual de TradingCore (solo lectura).",
    )
    parser.add_argument(
        "--earnings-limit",
        type=int,
        default=DEFAULT_EARNINGS_LIMIT,
        help="Numero maximo de eventos de earnings solicitados a Yahoo.",
    )
    parser.add_argument(
        "--match-window-days",
        type=int,
        default=DEFAULT_MATCH_WINDOW_DAYS,
        help="Ventana maxima para asociacion heuristica Yahoo fiscal -> earnings.",
    )
    parser.add_argument(
        "--av-delay",
        type=float,
        default=12.0,
        help="Pausa entre llamadas Alpha Vantage por ticker.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    fundamentals_path = Path(args.fundamentals_path)
    api_key = os.getenv("ALPHA_VANTAGE_KEY", "").strip()

    all_summaries = []
    all_comparisons = []
    diagnostics = []

    print("== TradingCore fundamental provider diagnostic ==")
    print(f"Symbols: {', '.join(args.symbols)}")
    print(f"Output:  {output_dir.resolve()}")
    print(f"Cache:   {fundamentals_path.resolve()}")
    print(f"Alpha Vantage key: {'configured' if api_key else 'NOT configured'}")
    print()

    for pos, symbol in enumerate(args.symbols, start=1):
        print(f"[{pos}/{len(args.symbols)}] {symbol}")

        yahoo_fiscal, yahoo_events, yahoo_warnings = fetch_yahoo(
            symbol,
            earnings_limit=args.earnings_limit,
        )
        yahoo_matched = match_yahoo_fiscal_to_reported(
            yahoo_fiscal,
            yahoo_events,
            max_days=args.match_window_days,
        )

        alpha_df, alpha_warnings = fetch_alpha_vantage(symbol, api_key)
        cache_df, cache_warnings = load_tradingcore_cache(
            symbol,
            fundamentals_path,
        )

        yahoo_matched.to_csv(
            output_dir / f"{symbol}_yahoo_fiscal.csv",
            index=False,
        )
        yahoo_events.to_csv(
            output_dir / f"{symbol}_yahoo_earnings_dates.csv",
            index=False,
        )
        alpha_df.to_csv(
            output_dir / f"{symbol}_alpha_vantage_earnings.csv",
            index=False,
        )
        cache_df.to_csv(
            output_dir / f"{symbol}_tradingcore_cache.csv",
            index=False,
        )

        comparison = compare_eps(symbol, yahoo_fiscal, alpha_df, cache_df)
        comparison.to_csv(
            output_dir / f"{symbol}_eps_comparison.csv",
            index=False,
        )

        if not comparison.empty:
            all_comparisons.append(comparison)

        all_summaries.append(
            summarize_provider(symbol, "yahoo_fiscal", yahoo_fiscal)
        )
        all_summaries.append(
            summarize_provider(
                symbol,
                "yahoo_earnings_dates",
                yahoo_events,
                fiscal_col="__none__",
                reported_col="reported_date",
            )
        )
        all_summaries.append(
            summarize_provider(symbol, "alpha_vantage", alpha_df)
        )
        all_summaries.append(
            summarize_provider(
                symbol,
                "tradingcore_cache",
                cache_df,
                reported_col="__none__",
            )
        )

        warnings = yahoo_warnings + alpha_warnings + cache_warnings
        for warning in warnings:
            diagnostics.append({"symbol": symbol, "warning": warning})
            print(f"  WARNING: {warning}")

        print(
            "  Yahoo fiscal:",
            len(yahoo_fiscal),
            "| Yahoo earnings dates:",
            len(yahoo_events),
            "| Alpha Vantage:",
            len(alpha_df),
            "| Cache:",
            len(cache_df),
        )

        if api_key and pos < len(args.symbols) and args.av_delay > 0:
            time.sleep(args.av_delay)

    summary_df = pd.DataFrame(all_summaries)
    summary_df.to_csv(output_dir / "provider_summary.csv", index=False)

    if all_comparisons:
        pd.concat(all_comparisons, ignore_index=True).to_csv(
            output_dir / "eps_comparison_all.csv",
            index=False,
        )

    pd.DataFrame(diagnostics).to_csv(
        output_dir / "diagnostics.csv",
        index=False,
    )

    metadata = {
        "symbols": args.symbols,
        "alpha_vantage_key_configured": bool(api_key),
        "yahoo_earnings_limit": args.earnings_limit,
        "yahoo_fiscal_to_reported_match_is_heuristic": True,
        "match_window_days": args.match_window_days,
        "fundamentals_path": str(fundamentals_path),
        "output_dir": str(output_dir),
        "writes_to_productive_fundamentals_cache": False,
        "writes_to_postgresql": False,
    }

    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("Diagnostic complete.")
    print(f"Summary: {output_dir / 'provider_summary.csv'}")
    print(f"Warnings: {output_dir / 'diagnostics.csv'}")
    print(f"Metadata: {output_dir / 'run_metadata.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
