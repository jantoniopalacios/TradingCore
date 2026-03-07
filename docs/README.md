# TradingCore: Motor Central y Arquitectura Modular

Este repositorio contiene la arquitectura central (Motor) para múltiples escenarios de trading (Backtesting, Live Trading, Web Apps).

---

## Inicio Rapido (Backtest Web)

Para ejecutar la aplicación web de backtesting desde la raíz del repo:

1. **Activar entorno virtual:**
   ```bash
   .\.venv\Scripts\activate
   ```
2. **Instalar dependencias (si aplica):**
   ```bash
   pip install -r requirements.txt
   ```
3. **Iniciar servidor Flask:**
   ```bash
   python scenarios/BacktestWeb/app.py
   ```
4. **Abrir la aplicación:**
   ```text
   http://localhost:5000
   ```

## Estructura del Repositorio

| Directorio | Contenido |
| :--- | :--- |
| `trading_engine/` | **El Motor Central** (Lógica de Trading). Código reutilizable. |
| `scenarios/BacktestWeb/` | Aplicación Flask para lanzar backtests y consultar resultados. |
| `scripts/` | Scripts de validación y pruebas funcionales del motor. |

---

## Documentacion Detallada

Documentación recomendada:

- Arquitectura canónica: **[ARCHITECTURE.md](ARCHITECTURE.md)**
- Flujo web de ejecución: **[Architecture/FLUJO_ARQUITECTURA_MEJORADO.md](Architecture/FLUJO_ARQUITECTURA_MEJORADO.md)**
- Índice general: **[Index/00_INDEX_DOCUMENTACION.md](Index/00_INDEX_DOCUMENTACION.md)**