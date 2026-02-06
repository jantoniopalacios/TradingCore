"""
Script FINAL: Backtest NKE con Configuración Global + EMA
Versión depurada y funcional

Ejecutar desde raíz del proyecto:
  python test_backtest_nke_final.py
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from trading_engine.indicators.Filtro_EMA import update_ema_state
from trading_engine.utils.Calculos_Tecnicos import verificar_estado_indicador

# ... rest of final script located in repo ...
