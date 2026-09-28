from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from trading_engine.fundamentals.providers.yahoo import YahooFundamentalProvider
from trading_engine.fundamentals.store import FundamentalStore


@dataclass(frozen=True)
class FundamentalUpdateResult:
    symbol: str
    status: str
    fetched_records: int
    stored_records: int
    unique_fiscal_periods: int
    first_fiscal_date: Optional[str]
    last_fiscal_date: Optional[str]
    message: Optional[str] = None


class FundamentalUpdater:
    """
    Actualiza fundamentales recientes para una lista explícita de símbolos.

    Esta primera versión usa solo Yahoo. Alpha Vantage se añadirá después como
    bootstrap histórico separado, para no mezclar mantenimiento ordinario con
    consumo de cuota histórica.
    """

    def __init__(
        self,
        store: FundamentalStore,
        yahoo_provider: YahooFundamentalProvider,
    ):
        self.store = store
        self.yahoo_provider = yahoo_provider

    @staticmethod
    def normalize_symbols(symbols: Iterable[str]) -> list[str]:
        seen = set()
        result = []

        for raw in symbols:
            symbol = str(raw).strip().upper()
            if not symbol or symbol in seen:
                continue

            seen.add(symbol)
            result.append(symbol)

        return result

    def update_symbol(self, symbol: str) -> FundamentalUpdateResult:
        symbol = str(symbol).strip().upper()
        if not symbol:
            raise ValueError("El símbolo no puede estar vacío.")

        try:
            records = self.yahoo_provider.fetch_records(symbol)
        except Exception as exc:
            summary = self.store.coverage_summary(symbol)
            return FundamentalUpdateResult(
                symbol=symbol,
                status="error",
                fetched_records=0,
                stored_records=summary["records"],
                unique_fiscal_periods=summary["unique_fiscal_periods"],
                first_fiscal_date=summary["first_fiscal_date"],
                last_fiscal_date=summary["last_fiscal_date"],
                message=str(exc),
            )

        if records:
            self.store.merge_records(symbol, records)

        summary = self.store.coverage_summary(symbol)

        if records:
            status = "updated"
            message = None
        elif summary["records"] > 0:
            status = "no_new_data"
            message = None
        else:
            status = "no_data"
            message = "Yahoo no devolvió fundamentales utilizables."

        return FundamentalUpdateResult(
            symbol=symbol,
            status=status,
            fetched_records=len(records),
            stored_records=summary["records"],
            unique_fiscal_periods=summary["unique_fiscal_periods"],
            first_fiscal_date=summary["first_fiscal_date"],
            last_fiscal_date=summary["last_fiscal_date"],
            message=message,
        )

    def update_symbols(
        self,
        symbols: Iterable[str],
    ) -> list[FundamentalUpdateResult]:
        """
        Actualiza exactamente el universo recibido.

        Esto permitirá conectar posteriormente:
            filtro_fundamental=True
                -> lista de activos configurada por el usuario
                -> update_symbols(lista_activos)
        """
        return [
            self.update_symbol(symbol)
            for symbol in self.normalize_symbols(symbols)
        ]
