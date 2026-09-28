from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Callable, Optional

import requests

from trading_engine.fundamentals.models import FundamentalRecord


class AlphaVantageError(RuntimeError):
    """Error genérico del proveedor Alpha Vantage."""


class AlphaVantageQuotaExhausted(AlphaVantageError):
    """La cuota/rate limit de Alpha Vantage se ha agotado."""


class AlphaVantageNoData(AlphaVantageError):
    """Alpha Vantage no devolvió histórico utilizable para el símbolo."""


class AlphaVantageFundamentalProvider:
    """
    Bootstrap histórico de EPS mediante Alpha Vantage EARNINGS.

    Reglas:
    - la API key solo se obtiene del entorno;
    - una llamada HTTP por símbolo;
    - no escribe nada por sí mismo;
    - detecta respuestas de cuota agotada y lanza una excepción específica;
    - los tests pueden inyectar `http_get` y no requieren red.
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(
        self,
        api_key: Optional[str] = None,
        http_get: Optional[Callable] = None,
        timeout_seconds: int = 30,
    ):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_KEY")
        self.http_get = http_get or requests.get
        self.timeout_seconds = int(timeout_seconds)

    def _require_api_key(self) -> str:
        if not self.api_key:
            raise AlphaVantageError(
                "Falta ALPHA_VANTAGE_KEY en el entorno."
            )
        return self.api_key

    @staticmethod
    def _quota_message(payload: dict) -> Optional[str]:
        for key in ("Note", "Information"):
            value = payload.get(key)
            if not value:
                continue

            text = str(value)
            lowered = text.lower()

            quota_markers = (
                "rate limit",
                "call frequency",
                "api calls",
                "standard api call frequency",
                "daily",
                "per day",
                "premium",
                "thank you for using alpha vantage",
            )
            if any(marker in lowered for marker in quota_markers):
                return text

        return None

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        if value in (None, "", "None", "null"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def fetch_records(self, symbol: str) -> list[FundamentalRecord]:
        symbol = str(symbol).strip().upper()
        if not symbol:
            raise ValueError("El símbolo no puede estar vacío.")

        api_key = self._require_api_key()

        response = self.http_get(
            self.BASE_URL,
            params={
                "function": "EARNINGS",
                "symbol": symbol,
                "apikey": api_key,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, dict):
            raise AlphaVantageError(
                "Respuesta inesperada de Alpha Vantage."
            )

        quota_message = self._quota_message(payload)
        if quota_message:
            raise AlphaVantageQuotaExhausted(quota_message)

        if payload.get("Error Message"):
            raise AlphaVantageNoData(str(payload["Error Message"]))

        rows = payload.get("quarterlyEarnings")
        if not rows:
            raise AlphaVantageNoData(
                f"Alpha Vantage no devolvió quarterlyEarnings para {symbol}."
            )

        now = datetime.now(timezone.utc)
        records: list[FundamentalRecord] = []

        for row in rows:
            fiscal_raw = row.get("fiscalDateEnding")
            reported_raw = row.get("reportedDate")
            eps = self._safe_float(row.get("reportedEPS"))

            if not fiscal_raw or not reported_raw or eps is None:
                continue

            try:
                fiscal_date = datetime.strptime(
                    fiscal_raw, "%Y-%m-%d"
                ).date()
                reported_date = datetime.strptime(
                    reported_raw, "%Y-%m-%d"
                ).date()
            except ValueError:
                continue

            records.append(
                FundamentalRecord(
                    symbol=symbol,
                    fiscal_date=fiscal_date,
                    reported_date=reported_date,
                    metric="diluted_eps",
                    value=eps,
                    provider="alpha_vantage",
                    source_type="earnings_reported_eps",
                    updated_at=now,
                )
            )

        if not records:
            raise AlphaVantageNoData(
                f"Alpha Vantage no devolvió EPS trimestral utilizable para {symbol}."
            )

        records.sort(key=lambda r: r.fiscal_date)
        return records
