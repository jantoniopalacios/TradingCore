from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from trading_engine.fundamentals.bootstrap import AlphaVantageBootstrapper
from trading_engine.fundamentals.store import FundamentalStore
from trading_engine.fundamentals.updater import FundamentalUpdater


@dataclass(frozen=True)
class FundamentalServiceResult:
    symbol: str
    yahoo_status: str
    bootstrap_status: str
    stored_records: int
    unique_fiscal_periods: int
    first_fiscal_date: Optional[str]
    last_fiscal_date: Optional[str]
    providers: list[str]
    message: Optional[str] = None


class FundamentalService:
    """Coordina la actualización Yahoo y el bootstrap histórico."""

    def __init__(
        self,
        store: FundamentalStore,
        updater: FundamentalUpdater,
        bootstrapper: AlphaVantageBootstrapper,
    ):
        self.store = store
        self.updater = updater
        self.bootstrapper = bootstrapper

    @staticmethod
    def normalize_symbols(symbols: Iterable[str]) -> list[str]:
        return FundamentalUpdater.normalize_symbols(symbols)

    def update_for_symbols(
        self,
        symbols: Iterable[str],
        bootstrap_missing: bool = True,
    ) -> list[FundamentalServiceResult]:
        normalized_symbols = self.normalize_symbols(symbols)
        yahoo_results = {
            result.symbol: result
            for result in self.updater.update_symbols(normalized_symbols)
        }

        bootstrap_results = {}
        if bootstrap_missing:
            bootstrap_results = {
                result.symbol: result
                for result in self.bootstrapper.run(normalized_symbols)
            }

        results = []
        for symbol in normalized_symbols:
            yahoo_result = yahoo_results.get(symbol)
            bootstrap_result = bootstrap_results.get(symbol)

            yahoo_status = yahoo_result.status if yahoo_result else "error"
            bootstrap_status = (
                bootstrap_result.status
                if bootstrap_missing and bootstrap_result is not None
                else "not_run" if bootstrap_missing else "not_requested"
            )

            messages = []
            if yahoo_result and yahoo_result.message:
                messages.append(f"Yahoo: {yahoo_result.message}")
            bootstrap_message = (
                bootstrap_result.message if bootstrap_result is not None else None
            )
            if bootstrap_message:
                messages.append(f"Alpha Vantage: {bootstrap_message}")

            coverage = self.store.coverage_summary(symbol)
            results.append(
                FundamentalServiceResult(
                    symbol=symbol,
                    yahoo_status=yahoo_status,
                    bootstrap_status=bootstrap_status,
                    stored_records=coverage["records"],
                    unique_fiscal_periods=coverage["unique_fiscal_periods"],
                    first_fiscal_date=coverage["first_fiscal_date"],
                    last_fiscal_date=coverage["last_fiscal_date"],
                    providers=coverage["providers"],
                    message="; ".join(messages) or None,
                )
            )

        return results
