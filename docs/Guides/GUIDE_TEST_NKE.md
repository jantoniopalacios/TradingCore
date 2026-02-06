```markdown
"""
Guía rápida para hacer el test de NKE
"""

# OPCIÓN 1: DESDE LA LÍNEA DE COMANDOS
# =====================================

# 1. Navega a la raíz del proyecto
cd c:\Users\juant\Proyectos\Python\TradingCore

# 2. Ejecuta el script de test
python test_backtest_nke.py

# Esto mostrará:
# - Carga de datos
# - Inicialización de indicadores
# - Ejecución del backtest
# - Métricas finales (Return, Sharpe, Max Drawdown, etc.)
# - Gráfico HTML interactivo


# OPCIÓN 2: DESDE LA INTERFAZ WEB
# ================================

# 1. Inicia la aplicación Flask
python -m scenarios.BacktestWeb.app

# 2. Abre en navegador
http://localhost:5000

# 3. Login (admin / admin)

# 4. Configura:
#    - TAB "Símbolos": Cambia a solo "NKE"
#    - TAB "Parámetros Globales":
#        - Fecha inicio: (ej: 2020-01-01)
#        - Fecha fin: (ej: 2023-12-31)
#        - Capital: 10000
#        - Comisión: 0.002
#        - Stop Loss: 0.05 (5%)
#
#    - TAB "EMA":
#        ✓ Activar cruce
#        ✓ EMA Rápida: 12
#        ✓ EMA Lenta: 26
#        ✓ Bloquear en descendente
#        ✓ Vender cuando baja

# 5. Guarda configuración

# 6. Haz clic en "Iniciar Backtest"

# 7. Revisa:
#    - TAB "Historial" → Resultados agrupados
#    - TAB "Gráficos" → Visualización interactiva
#    - TAB "Archivos" → Logs detallados


# PARÁMETROS QUE PUEDES VARIAR PARA EXPERIMENTAR
# ================================================

# 1. EMA Rápida: Prueba 5, 10, 12, 20
# 2. EMA Lenta: Prueba 26, 30, 50, 100
# 3. Filtros EMA:
#    - Sin filtros (solo cruce)
#    - Con bloqueo en descendente (no comprar si baja)
#    - Con requerimiento de ascendente (comprar solo si sube)
#    - Con bloqueo en máximo (no comprar en extremos altos)
#
# 4. Stop Loss: 0.03 (3%), 0.05 (5%), 0.07 (7%), 0.10 (10%)
# 5. Capital: 5000, 10000, 50000, 100000
# 6. Rango de fechas: Años diferentes para ver rendimiento en distintos mercados
# 7. Intervalo: Prueba '1d', '1h', '1wk'


# CÓMO INTERPRETAR LOS RESULTADOS
# ================================

# Return (%) 
#   → Ganancia/Pérdida total (objetivo: > Buy & Hold)
#
# Buy & Hold Return (%)
#   → Retorno si solo comprabas y guardabas
#   → La estrategia debería superar esto
#
# Total Trades
#   → Número de operaciones (más no siempre es mejor)
#
# Win Rate (%)
#   → Porcentaje de trades ganadores (objetivo: > 50%)
#
# Sharpe Ratio
#   → Retorno ajustado por riesgo (> 1.0 es bueno, > 2.0 excelente)
#
# Max Drawdown (%)
#   → Peor pérdida desde máximo (objetivo: < 20%)
#
# Profit Factor
#   → Ratio ganancia/pérdida (objetivo: > 1.5)


# INFORMACIÓN TÉCNICA DEL TEST
# ============================

# Datos:
#   - Fuente: Data_files/NKE_1d_MAX.csv (histórico completo disponible)
#   - Activo: Nike (NKE)
#   - Intervalo: Diario (1d)
#
# Configuración Base:
#   - Capital: $10,000
#   - Comisión: 0.2%
#   - Sin apalancamiento
#
# Indicadores:
#   - EMA Rápida (12 períodos)
#   - EMA Lenta (26 períodos)
#   - Cruce como señal de entrada
#
# Lógica de Compra (OR):
#   → EMA Rápida cruza sobre EMA Lenta
#
# Filtros (AND):
#   → (Opcional) No comprar si EMA está descendiendo
#   → (Opcional) No comprar si está en máximo histórico
#
# Lógica de Venta:
#   → Stop Loss: 5% por debajo del precio de entrada
#   → Técnico: Cuando EMA Lenta gira descendente (si activado)


# PRÓXIMOS PASOS DESPUÉS DEL TEST
# ================================

# 1. Compara rendimientos con diferentes períodos de EMA
# 2. Prueba agregar más indicadores (RSI, MACD, etc.)
# 3. Optimiza los parámetros para maximizar Sharpe Ratio
# 4. Valida en otros activos (AAPL, MSFT, etc.)
# 5. Exporta resultados y úsalos en decisiones reales

```
