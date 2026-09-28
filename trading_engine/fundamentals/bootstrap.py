from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Optional

from trading_engine.fundamentals.providers.alpha_vantage import (
    AlphaVantageFundamentalProvider,
    AlphaVantageNoData,
    AlphaVantageQuotaExhausted,
)
from trading_engine.fundamentals.store import FundamentalStore


@dataclass
class BootstrapSymbolState:
    status: str = "pending"
    last_attempt: Optional[str] = None
    completed_at: Optional[str] = None
    message: Optional[str] = None


@dataclass(frozen=True)
class BootstrapResult:
    symbol: str
    status: str
    fetched_records: int
    message: Optional[str] = None


class BootstrapStateStore:
    """
    Estado persistente del bootstrap histórico de Alpha Vantage.

    El fichero se mantiene separado de los CSV fundamentales para que el
    histórico financiero y el estado operativo no se mezclen.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, BootstrapSymbolState]:
        if not self.path.exists():
            return {}

        with self.path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)

        result = {}
        for symbol, values in raw.items():
            result[str(symbol).upper()] = BootstrapSymbolState(
                status=values.get("status", "pending"),
                last_attempt=values.get("last_attempt"),
                completed_at=values.get("completed_at"),
                message=values.get("message"),
            )
        return result

    def save(self, state: dict[str, BootstrapSymbolState]) -> None:
        serializable = {
            symbol: asdict(values)
            for symbol, values in sorted(state.items())
        }

        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(
                serializable,
                fh,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            fh.write("\n")

        tmp.replace(self.path)


class AlphaVantageBootstrapper:
    """
    Construye histórico inicial mediante Alpha Vantage.

    Política:
    - los símbolos `completed` no vuelven a descargarse;
    - `no_data` se considera terminal hasta que el usuario decida reintentarlo;
    - errores ordinarios se registran y se continúa con el siguiente símbolo;
    - si se detecta cuota agotada, se detiene inmediatamente el lote;
    - el símbolo bloqueado por cuota queda `quota_blocked` y puede reintentarse
      en una ejecución posterior.
    """

    def __init__(
        self,
        store: FundamentalStore,
        provider: AlphaVantageFundamentalProvider,
        state_store: BootstrapStateStore,
    ):
        self.store = store
        self.provider = provider
        self.state_store = state_store

    @staticmethod
    def _normalize_symbols(symbols: Iterable[str]) -> list[str]:
        seen = set()
        result = []

        for raw in symbols:
            symbol = str(raw).strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            result.append(symbol)

        return result

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def run(self, symbols: Iterable[str]) -> list[BootstrapResult]:
        state = self.state_store.load()
        results: list[BootstrapResult] = []

        for symbol in self._normalize_symbols(symbols):
            symbol_state = state.get(symbol, BootstrapSymbolState())

            if symbol_state.status == "completed":
                results.append(
                    BootstrapResult(
                        symbol=symbol,
                        status="skipped_completed",
                        fetched_records=0,
                    )
                )
                continue

            if symbol_state.status == "no_data":
                results.append(
                    BootstrapResult(
                        symbol=symbol,
                        status="skipped_no_data",
                        fetched_records=0,
                        message=symbol_state.message,
                    )
                )
                continue

            attempt_time = self._now_iso()
            symbol_state.status = "in_progress"
            symbol_state.last_attempt = attempt_time
            symbol_state.completed_at = None
            symbol_state.message = None
            state[symbol] = symbol_state
            self.state_store.save(state)

            try:
                records = self.provider.fetch_records(symbol)

            except AlphaVantageQuotaExhausted as exc:
                symbol_state.status = "quota_blocked"
                symbol_state.message = str(exc)
                state[symbol] = symbol_state
                self.state_store.save(state)

                results.append(
                    BootstrapResult(
                        symbol=symbol,
                        status="quota_blocked",
                        fetched_records=0,
                        message=str(exc),
                    )
                )
                break

            except AlphaVantageNoData as exc:
                symbol_state.status = "no_data"
                symbol_state.message = str(exc)
                state[symbol] = symbol_state
                self.state_store.save(state)

                results.append(
                    BootstrapResult(
                        symbol=symbol,
                        status="no_data",
                        fetched_records=0,
                        message=str(exc),
                    )
                )
                continue

            except Exception as exc:
                symbol_state.status = "error"
                symbol_state.message = str(exc)
                state[symbol] = symbol_state
                self.state_store.save(state)

                results.append(
                    BootstrapResult(
                        symbol=symbol,
                        status="error",
                        fetched_records=0,
                        message=str(exc),
                    )
                )
                continue

            self.store.merge_records(symbol, records)

            coverage = self.store.coverage_summary(symbol)
            if coverage["unique_fiscal_periods"] >= 20:
                symbol_state.status = "completed"
                symbol_state.completed_at = self._now_iso()
            else:
                symbol_state.status = "partial"
            symbol_state.message = None
            state[symbol] = symbol_state
            self.state_store.save(state)

            results.append(
                BootstrapResult(
                    symbol=symbol,
                    status=symbol_state.status,
                    fetched_records=len(records),
                )
            )

        return results

    def reset_symbol(self, symbol: str) -> None:
        """
        Permite volver a poner manualmente un símbolo en pendiente.

        No borra el histórico existente.
        """
        symbol = str(symbol).strip().upper()
        if not symbol:
            raise ValueError("El símbolo no puede estar vacío.")

        state = self.state_store.load()
        state[symbol] = BootstrapSymbolState(status="pending")
        self.state_store.save(state)
