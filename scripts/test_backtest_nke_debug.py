"""
Script DEBUG: Backtest NKE con mensajes detallados en cada paso
Propósito: Identificar exactamente dónde se detiene la ejecución

Ejecutar desde raíz del proyecto:
  python test_backtest_nke_debug.py
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# ================================================================
# --- SETUP DE RUTAS ---
# ================================================================
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print(f"[DEBUG] Project root: {project_root}", flush=True)
print(f"[DEBUG] sys.path[0]: {sys.path[0]}", flush=True)

# ================================================================
# --- IMPORTS ---
# ================================================================
print("\n[STEP 1] Importando librerías...")
sys.stdout.flush()

try:
    from backtesting import Backtest, Strategy
    print("  ✅ backtesting importado")
except Exception as e:
    print(f"  ❌ Error importando backtesting: {e}")
    sys.exit(1)

try:
    from backtesting.lib import crossover
    print("  ✅ crossover importado")
except Exception as e:
    print(f"  ❌ Error importando crossover: {e}")
    sys.exit(1)

try:
    from trading_engine.indicators.Filtro_EMA import update_ema_state
    print("  ✅ update_ema_state importado")
except Exception as e:
    print(f"  ❌ Error importando update_ema_state: {e}")
    sys.exit(1)

try:
    from trading_engine.utils.Calculos_Tecnicos import verificar_estado_indicador
    print("  ✅ verificar_estado_indicador importado")
except Exception as e:
    print(f"  ❌ Error importando verificar_estado_indicador: {e}")
    sys.exit(1)

print("[STEP 1] ✅ Todos los imports completados\n", flush=True)
sys.stdout.flush()

# ... rest of debug script (already available in repo) ...
