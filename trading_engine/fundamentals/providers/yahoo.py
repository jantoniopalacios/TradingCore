from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, Iterable, Optional

import pandas as pd

from trading_engine.fundamentals.models import FundamentalRecord


@dataclass(frozen=True)
class YahooFiscalEPS:
    fiscal_date: date
    diluted_eps: float


@dataclass(frozen=True)
class YahooReportedEPS:
    reported_date: date
    reported_eps: float


class YahooFundamentalProvider:
    """
    Adaptador de Yahoo/yfinance hacia el modelo normalizado de TradingCore.

    Diseño conservador:
    - `quarterly_income_stmt` aporta fiscal_date + Diluted EPS.
    - `earnings_dates` aporta reported_date + Reported EPS.
    - Solo se crea un FundamentalRecord utilizable históricamente cuando existe
      una asociación explícita entre ambos conjuntos.
    - No se inventa reported_date usando fiscal_date ni offsets fijos.
    - Los tests pueden inyectar un ticker_factory falso y no requieren red.

    Nota:
    Yahoo no expone necesariamente una clave fiscal común entre ambos endpoints.
    Por ello el emparejamiento por defecto usa proximidad temporal hacia delante,
    con una ventana máxima configurable. Ese emparejamiento es una heurística de
    ingestión y debe quedar trazable mediante `source_type`.
    """

    def __init__(
        self,
        ticker_factory: Optional[Callable[[str], object]] = None,
        max_report_lag_days: int = 120,
    ):
        if max_report_lag_days <= 0:
            raise ValueError("max_report_lag_days debe ser mayor que cero.")

        self._ticker_factory = ticker_factory
        self.max_report_lag_days = int(max_report_lag_days)

    def _make_ticker(self, symbol: str):
        if self._ticker_factory is not None:
            return self._ticker_factory(symbol)

        import yfinance as yf

        return yf.Ticker(symbol)

    @staticmethod
    def _coerce_date(value) -> Optional[date]:
        if value is None or pd.isna(value):
            return None

        ts = pd.Timestamp(value)
        if ts.tzinfo is not None:
            ts = ts.tz_convert(None)
        return ts.date()

    @staticmethod
    def _coerce_float(value) -> Optional[float]:
        if value is None or pd.isna(value):
            return None

        try:
            result = float(value)
        except (TypeError, ValueError):
            return None

        if not pd.notna(result):
            return None

        return result

    @staticmethod
    def _find_row_case_insensitive(
        frame: pd.DataFrame,
        candidates: Iterable[str],
    ) -> Optional[pd.Series]:
        if frame is None or frame.empty:
            return None

        normalized = {
            str(index).strip().lower(): index
            for index in frame.index
        }

        for candidate in candidates:
            original = normalized.get(candidate.strip().lower())
            if original is not None:
                return frame.loc[original]

        return None

    @staticmethod
    def _find_column_case_insensitive(
        frame: pd.DataFrame,
        candidates: Iterable[str],
    ) -> Optional[str]:
        if frame is None or frame.empty:
            return None

        normalized = {
            str(column).strip().lower(): column
            for column in frame.columns
        }

        for candidate in candidates:
            original = normalized.get(candidate.strip().lower())
            if original is not None:
                return original

        return None

    def fetch_fiscal_eps(self, symbol: str) -> list[YahooFiscalEPS]:
        """
        Lee Diluted EPS del estado de resultados trimestral de Yahoo.
        """
        ticker = self._make_ticker(symbol)
        frame = ticker.get_income_stmt(freq="quarterly", pretty=True)

        if frame is None or frame.empty:
            return []

        eps_row = self._find_row_case_insensitive(
            frame,
            candidates=(
                "Diluted EPS",
                "DilutedEPS",
            ),
        )
        if eps_row is None:
            return []

        rows: list[YahooFiscalEPS] = []
        for fiscal_raw, eps_raw in eps_row.items():
            fiscal_date = self._coerce_date(fiscal_raw)
            eps = self._coerce_float(eps_raw)

            if fiscal_date is None or eps is None:
                continue

            rows.append(
                YahooFiscalEPS(
                    fiscal_date=fiscal_date,
                    diluted_eps=eps,
                )
            )

        rows.sort(key=lambda row: row.fiscal_date)
        return rows

    def fetch_reported_eps(self, symbol: str) -> list[YahooReportedEPS]:
        """
        Lee Reported EPS y la fecha del evento de earnings de Yahoo.
        """
        ticker = self._make_ticker(symbol)
        frame = ticker.get_earnings_dates(limit=100)

        if frame is None or frame.empty:
            return []

        eps_col = self._find_column_case_insensitive(
            frame,
            candidates=(
                "Reported EPS",
                "ReportedEPS",
            ),
        )
        if eps_col is None:
            return []

        rows: list[YahooReportedEPS] = []
        for reported_raw, item in frame.iterrows():
            reported_date = self._coerce_date(reported_raw)
            eps = self._coerce_float(item.get(eps_col))

            if reported_date is None or eps is None:
                continue

            rows.append(
                YahooReportedEPS(
                    reported_date=reported_date,
                    reported_eps=eps,
                )
            )

        rows.sort(key=lambda row: row.reported_date)
        return rows

    def _match_reported_date(
        self,
        fiscal: YahooFiscalEPS,
        reported_rows: list[YahooReportedEPS],
    ) -> Optional[YahooReportedEPS]:
        """
        Busca el primer earnings event posterior al cierre fiscal y dentro de
        `max_report_lag_days`.

        No usa similitud de EPS como criterio principal, porque proveedores y
        endpoints pueden representar definiciones distintas de EPS.
        """
        candidates = []
        for reported in reported_rows:
            lag = (reported.reported_date - fiscal.fiscal_date).days

            if lag < 0:
                continue
            if lag > self.max_report_lag_days:
                continue

            candidates.append((lag, reported))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def fetch_records(self, symbol: str) -> list[FundamentalRecord]:
        """
        Devuelve EPS diluido normalizado.

        El valor principal procede del estado financiero (`Diluted EPS`), pero
        la disponibilidad histórica procede de la fecha del earnings event.
        `source_type` deja explícita esta combinación.
        """
        normalized_symbol = str(symbol).strip().upper()
        if not normalized_symbol:
            raise ValueError("El símbolo no puede estar vacío.")

        fiscal_rows = self.fetch_fiscal_eps(normalized_symbol)
        reported_rows = self.fetch_reported_eps(normalized_symbol)

        now = datetime.now(timezone.utc)
        result: list[FundamentalRecord] = []

        for fiscal in fiscal_rows:
            reported = self._match_reported_date(fiscal, reported_rows)
            if reported is None:
                continue

            result.append(
                FundamentalRecord(
                    symbol=normalized_symbol,
                    fiscal_date=fiscal.fiscal_date,
                    reported_date=reported.reported_date,
                    metric="diluted_eps",
                    value=fiscal.diluted_eps,
                    provider="yahoo",
                    source_type=(
                        "income_stmt_diluted_eps+earnings_dates_reported_date"
                    ),
                    updated_at=now,
                )
            )

        return result
