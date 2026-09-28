from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from .models import FundamentalRecord


STORE_COLUMNS = [
    "symbol",
    "fiscal_date",
    "reported_date",
    "metric",
    "value",
    "provider",
    "source_type",
    "updated_at",
]


class FundamentalStore:
    """
    Persistencia CSV acumulativa de fundamentales normalizados.

    Reglas principales:
    - un fichero por símbolo;
    - no usar nombres Q1/Q2/Q3/Q4;
    - conservar la procedencia;
    - no sobrescribir automáticamente valores de proveedores distintos;
    - ordenar por fecha fiscal, métrica y proveedor;
    - permitir seleccionar únicamente datos ya publicados en una fecha dada.
    """

    def __init__(self, base_path: Path | str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        normalized = str(symbol).strip().upper()
        if not normalized:
            raise ValueError("El símbolo no puede estar vacío.")
        return normalized

    def path_for_symbol(self, symbol: str) -> Path:
        symbol = self.normalize_symbol(symbol)
        return self.base_path / f"{symbol}.csv"

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame(columns=STORE_COLUMNS)

    @staticmethod
    def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return FundamentalStore._empty_df()

        out = df.copy()

        for col in STORE_COLUMNS:
            if col not in out.columns:
                out[col] = pd.NA

        out = out[STORE_COLUMNS]

        out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
        out["metric"] = out["metric"].astype(str).str.strip().str.lower()
        out["provider"] = out["provider"].astype(str).str.strip().str.lower()
        out["source_type"] = out["source_type"].astype(str).str.strip().str.lower()

        out["fiscal_date"] = pd.to_datetime(
            out["fiscal_date"], errors="coerce"
        ).dt.normalize()
        out["reported_date"] = pd.to_datetime(
            out["reported_date"], errors="coerce"
        ).dt.normalize()
        out["updated_at"] = pd.to_datetime(
            out["updated_at"], errors="coerce", utc=True
        )
        out["value"] = pd.to_numeric(out["value"], errors="coerce")

        out = out.dropna(
            subset=["symbol", "fiscal_date", "metric", "value", "provider"]
        )

        # Duplicado exacto de procedencia: conservar la versión más reciente.
        out = out.sort_values("updated_at", na_position="first")
        out = out.drop_duplicates(
            subset=["symbol", "fiscal_date", "metric", "provider"],
            keep="last",
        )

        return out.sort_values(
            ["symbol", "fiscal_date", "metric", "provider"]
        ).reset_index(drop=True)

    def load(self, symbol: str) -> pd.DataFrame:
        path = self.path_for_symbol(symbol)
        if not path.exists():
            return self._empty_df()

        df = pd.read_csv(path, sep=";")
        return self._normalize_df(df)

    def save(self, symbol: str, df: pd.DataFrame) -> Path:
        symbol = self.normalize_symbol(symbol)
        normalized = self._normalize_df(df)

        if not normalized.empty:
            wrong_symbols = normalized.loc[
                normalized["symbol"] != symbol, "symbol"
            ].unique()
            if len(wrong_symbols):
                raise ValueError(
                    f"El DataFrame contiene símbolos ajenos a {symbol}: "
                    f"{wrong_symbols.tolist()}"
                )

        path = self.path_for_symbol(symbol)
        normalized.to_csv(
            path,
            sep=";",
            index=False,
            date_format="%Y-%m-%d",
        )
        return path

    def merge_records(
        self,
        symbol: str,
        records: Iterable[FundamentalRecord],
    ) -> pd.DataFrame:
        """
        Fusiona registros nuevos con el histórico existente.

        Los proveedores distintos se conservan como filas distintas. Dentro de
        un mismo proveedor, fecha fiscal y métrica, prevalece la observación con
        `updated_at` más reciente.
        """
        symbol = self.normalize_symbol(symbol)
        current = self.load(symbol)

        rows = []
        for record in records:
            if self.normalize_symbol(record.symbol) != symbol:
                raise ValueError(
                    f"Registro de {record.symbol} no pertenece a {symbol}."
                )

            rows.append({
                "symbol": symbol,
                "fiscal_date": record.fiscal_date,
                "reported_date": record.reported_date,
                "metric": record.metric,
                "value": record.value,
                "provider": record.provider,
                "source_type": record.source_type,
                "updated_at": record.updated_at,
            })

        incoming = pd.DataFrame(rows, columns=STORE_COLUMNS)
        if current.empty:
            merged = incoming.copy()
        elif incoming.empty:
            merged = current.copy()
        else:
            merged = pd.concat([current, incoming], ignore_index=True)
        normalized = self._normalize_df(merged)
        self.save(symbol, normalized)
        return normalized

    def available_as_of(
        self,
        symbol: str,
        as_of: date | datetime | str,
        metric: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Devuelve solo datos que ya estaban publicados en `as_of`.

        Esta función expresa la regla anti-look-ahead del nuevo diseño:
        `reported_date` determina la disponibilidad para el backtest.
        """
        df = self.load(symbol)
        if df.empty:
            return df

        as_of_ts = pd.Timestamp(as_of).normalize()

        available = df[
            df["reported_date"].notna()
            & (df["reported_date"] <= as_of_ts)
        ].copy()

        if metric is not None:
            metric_norm = str(metric).strip().lower()
            available = available[available["metric"] == metric_norm]

        return available.reset_index(drop=True)

    def latest_by_provider(
        self,
        symbol: str,
        metric: str,
        provider: str,
    ) -> Optional[pd.Series]:
        df = self.load(symbol)
        if df.empty:
            return None

        metric = metric.strip().lower()
        provider = provider.strip().lower()
        subset = df[
            (df["metric"] == metric)
            & (df["provider"] == provider)
        ]

        if subset.empty:
            return None

        return subset.sort_values("fiscal_date").iloc[-1]

    def coverage_summary(
        self,
        symbol: str,
        metric: str = "diluted_eps",
    ) -> dict:
        df = self.load(symbol)
        metric = metric.strip().lower()
        subset = df[df["metric"] == metric].copy()

        if subset.empty:
            return {
                "symbol": self.normalize_symbol(symbol),
                "metric": metric,
                "records": 0,
                "unique_fiscal_periods": 0,
                "first_fiscal_date": None,
                "last_fiscal_date": None,
                "providers": [],
            }

        fiscal_dates = pd.to_datetime(
            subset["fiscal_date"], errors="coerce"
        ).dropna()

        return {
            "symbol": self.normalize_symbol(symbol),
            "metric": metric,
            "records": int(len(subset)),
            "unique_fiscal_periods": int(subset["fiscal_date"].nunique()),
            "first_fiscal_date": (
                fiscal_dates.min().date().isoformat()
                if not fiscal_dates.empty
                else None
            ),
            "last_fiscal_date": (
                fiscal_dates.max().date().isoformat()
                if not fiscal_dates.empty
                else None
            ),
            "providers": sorted(subset["provider"].dropna().unique().tolist()),
        }


def make_record(
    *,
    symbol: str,
    fiscal_date: date,
    reported_date: Optional[date],
    metric: str,
    value: float,
    provider: str,
    source_type: str,
) -> FundamentalRecord:
    """Helper pequeño para productores/importadores futuros."""
    return FundamentalRecord(
        symbol=symbol,
        fiscal_date=fiscal_date,
        reported_date=reported_date,
        metric=metric,
        value=float(value),
        provider=provider,
        source_type=source_type,
        updated_at=datetime.now(timezone.utc),
    )
