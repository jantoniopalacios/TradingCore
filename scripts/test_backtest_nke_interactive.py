"""
Script INTERACTIVO para experimentar con diferentes configuraciones de NKE
Permite variar parámetros sin editar código

Ejecutar: python test_backtest_nke_interactive.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backtesting import Backtest
from backtesting.lib import crossover
from trading_engine.indicators.Filtro_EMA import update_ema_state
from trading_engine.utils.Calculos_Tecnicos import verificar_estado_indicador

# ... rest of interactive script available in repo ...
