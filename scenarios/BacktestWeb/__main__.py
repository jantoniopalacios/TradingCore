# ----------------------------------------------------------------------
# --- __main__.py ---
# ----------------------------------------------------------------------
# Descripción       : Punto de entrada para ejecutar la aplicación Flask de BacktestWeb
#               Permite iniciar el servidor directamente desde este módulo.
#         
# Fecha de modificación : 2026-02-01
# ----------------------------------------------------------------------

import os
from .app import run_app

# 2. Corremos el servidor
if __name__ == '__main__':
    run_app()