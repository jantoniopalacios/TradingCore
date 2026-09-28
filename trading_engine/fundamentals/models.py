from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class FundamentalRecord:
    """
    Registro normalizado de una métrica fundamental.

    `fiscal_date` identifica el periodo financiero al que pertenece el dato.
    `reported_date` identifica desde cuándo el dato podía ser conocido por el mercado.
    """

    symbol: str
    fiscal_date: date
    reported_date: Optional[date]
    metric: str
    value: float
    provider: str
    source_type: str
    updated_at: datetime

    def identity_key(self) -> tuple[str, date, str, str]:
        """
        Identidad de procedencia del registro.

        Se incluye `provider` deliberadamente para conservar discrepancias entre
        proveedores en lugar de sobrescribirlas de forma automática.
        """
        return (
            self.symbol.upper().strip(),
            self.fiscal_date,
            self.metric.strip().lower(),
            self.provider.strip().lower(),
        )
