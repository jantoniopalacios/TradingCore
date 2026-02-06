# ----------------------------------------------------------------------
# --- __main__.py ---
# ----------------------------------------------------------------------
# Descripción       : Punto de entrada para ejecutar la aplicación Flask de BacktestWeb
#               Permite iniciar el servidor directamente desde este módulo.
#         
# Fecha de modificación : 2026-02-01
# ----------------------------------------------------------------------

import os
from .app import create_app

# 1. Ejecutamos la función factory para obtener la instancia de la aplicación
app = create_app()

# 2. Corremos el servidor
if __name__ == '__main__':
    # Podemos usar app.run() aquí para un control total del servidor
    # o simplemente dejar el bloque if para que funcione con el comando de Flask
    # En este caso, lo ejecutaremos directamente:
    app.run(debug=True)