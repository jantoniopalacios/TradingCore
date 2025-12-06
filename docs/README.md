# 📈 TradingCore: Motor Central y Arquitectura Modular

Este repositorio contiene la arquitectura central (Motor) para múltiples escenarios de trading (Backtesting, Live Trading, Web Apps).

---

## 🚀 Inicio Rápido (Escenario Local)

Para ejecutar el escenario de Backtesting Local:

1.  **Navegar al Escenario:**
    ```bash
    cd scenarios/BacktestLocal
    ```
2.  **Crear y Activar Entorno Virtual:**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    ```
3.  **Instalar Motor Central y Dependencias:**
    ```bash
    pip install -r requirements.txt
    pip install -e ../../engines/trading_engine # Instala el motor
    ```
4.  **Ejecutar el Backtest:**
    ```bash
    python test_backtest.py
    ```

## 🛠️ Estructura del Repositorio

| Directorio | Contenido |
| :--- | :--- |
| `engines/trading_engine/` | **El Motor Central** (Lógica de Trading). Código reutilizable. |
| `scenarios/BacktestLocal/` | Proyecto de backtesting local, que consume el motor. |
| `scenarios/TradingWebLive/` | (Futuro) Proyecto de ejecución en vivo (web o API). |

---

## 💡 Documentación Detallada

Para comprender la **Arquitectura, Clases, Interfaces y Diseño Funcional** del motor, consulte:

➡️ **[ARCHITECTURE.md](ARCHITECTURE.md)**