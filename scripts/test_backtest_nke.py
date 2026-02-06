"""
Script de TEST: Backtest simple con NKE usando Configuración Global + EMA
Propósito: Validar el flujo de ejecución del motor central

Ejecutar desde la raíz del proyecto:
  python test_backtest_nke.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ================================================================
# --- SETUP DE RUTAS ---
# ================================================================
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# ================================================================
# --- IMPORTS DEL MOTOR ---
# ================================================================
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from trading_engine.core.Logica_Trading import check_buy_signal, manage_existing_position
from trading_engine.indicators.Filtro_EMA import (
    update_ema_state, check_ema_buy_signal, apply_ema_global_filter, check_ema_sell_signal
)
from trading_engine.utils.Calculos_Tecnicos import verificar_estado_indicador

# ... (rest of file omitted for brevity; original moved to scripts folder)
