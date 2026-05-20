# engines/trading_engine/src/trading_engine/core/Backtest_Runner.py

import pandas as pd
from backtesting import Backtest
from backtesting import Strategy
from typing import Type, List, Dict, Any, Tuple
import logging

# Se importa Logica_Trading para asegurar que se carga antes de la ejecución
from trading_engine.core import Logica_Trading 
from trading_engine.core.constants import COLUMNAS_HISTORICO # Reutilizamos la constante de columnas
from trading_engine.core.constants import REQUIRED_COLS # Si tienes esta constante, asegúrate de que esté en constants.py

logger = logging.getLogger("Backtest_Runner")
StrategySelf = Type[Strategy] 


def _safe_float(value, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return float(default)
    text = str(value).strip().replace(',', '.')
    if text == '':
        return float(default)
    try:
        return float(text)
    except Exception:
        return float(default)

# ----------------------------------------------------------------------
# --- FUNCIONES CENTRALES DEL MOTOR DE EJECUCIÓN ---
# ----------------------------------------------------------------------

def run_backtest_for_symbol(
    data_clean: pd.DataFrame,
    strategy_class: StrategySelf,
    symbol: str,
    cash: float,
    commission: float,
    stoploss_percentage: float,
    logger: logging.Logger
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Backtest]:
    """
    Ejecuta un backtest para un único símbolo.
    
    Retorna: (Estadísticas, Log de Trades, Objeto Backtest)
    """

    # --- Configurar variables de control por símbolo (inyección en la clase) ---
    strategy_class.ticker = symbol 
    strategy_class.trades_list = [] # Limpiar la lista de trades antes de cada ejecución
    strategy_class.stoploss_percentage_below_close = stoploss_percentage 
    
    logger.info(f"Símbolo {symbol}: Ejecutando backtest con Cash={cash}, Commission={commission}")

    # 🎯 INICIALIZACIÓN Y EJECUCIÓN DEL BACKTEST 🎯
    bt = Backtest(
        data_clean,
        strategy_class, 
        cash=cash,
        commission=commission,
        trade_on_close=True,
        finalize_trades=True
    )

    stats = bt.run()
    
    # Recolección de Resultados (Stats)
    stats_dict = stats.copy()
    
    # Recolección de Trades
    trades_log = stats._strategy.trades_list
    
    # 🔧 ORDENAR TRADES POR FECHA (Fix para problema de ordenamiento temporal)
    if trades_log and len(trades_log) > 0:
        # Ordenar por fecha de entrada (o fecha disponible)
        try:
            trades_log = sorted(trades_log, key=lambda x: x.get('Fecha', x.get('Entry Time', '')))
        except Exception:
            # Si falla el ordenamiento, al menos logear el warning
            logger.warning(f"No se pudo ordenar trades_log para {symbol}")
    
    # Se devuelve el objeto bt para que el ESCENARIO (Web) pueda generar el gráfico HTML.
    return stats_dict, trades_log, bt

# ----------------------------------------------------------------------

def run_multi_symbol_backtest(
    stocks_data: Dict[str, pd.DataFrame],
    strategy_class: StrategySelf,
    params_generales: Dict[str, Any],
    symbols_to_process: List[str],
    required_period: int,
    logger: logging.Logger
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Backtest]]:
    """
    Función maestra para ejecutar el backtest en múltiples símbolos, devolviendo resultados 
    estructurados y los objetos Backtest para la generación de gráficos en el escenario.
    """
    
    resultados_finales = []
    all_trades = []
    # Almacena los objetos Backtest (bt) por símbolo
    backtest_objects = {} 
    
    # Extracción de parámetros genéricos
    cash = _safe_float(params_generales.get('cash', 10000), 10000.0)
    commission = _safe_float(params_generales.get('commission', 0.0), 0.0)
    stoploss_percentage = _safe_float(params_generales.get('stoploss_percentage_below_close', 0.0), 0.0)
    
    # Definición de columnas requeridas (usando la constante de core)
    # NOTA: Asegúrate de que REQUIRED_COLS esté definido en trading_engine.core.constants
    # Determina columnas requeridas según config
    fundamental_active = params_generales.get('Margen_Seguridad_Active', False)
    base_cols = ["Open", "High", "Low", "Close", "Volume"]
    fundamental_cols = ["Margen de seguridad", "LTM EPS"]

    for symbol in symbols_to_process:
        logger.info(f"--- Procesando (Runner): {symbol} ---")
        data_for_symbol = stocks_data.get(symbol)
        if data_for_symbol is None:
            logger.warning(f"Símbolo {symbol}: Datos no encontrados. Saltando.")
            continue

        # Selecciona columnas según si el filtro fundamental está activo
        if fundamental_active:
            required_cols = base_cols + fundamental_cols
        else:
            required_cols = base_cols

        # Solo filtra columnas que existan en el DataFrame
        cols_present = [col for col in required_cols if col in data_for_symbol.columns]
        data_clean = data_for_symbol[cols_present].copy().dropna()

        if data_clean.empty or len(data_clean) < required_period:
            logger.warning(f"Símbolo {symbol}: Datos insuficientes después de limpieza ({len(data_clean)} velas). Mínimo requerido: {required_period}. Saltando.")
            continue

        # 2. Ejecutar backtest para el símbolo
        try:
            stats_dict, trades_log, bt_obj = run_backtest_for_symbol(
                data_clean,
                strategy_class,
                symbol,
                cash,
                commission,
                stoploss_percentage,
                logger
            )
        except Exception as e:
            logger.exception(f"Error CRÍTICO durante la ejecución del backtest para {symbol}")
            continue

        # 3. Recolección de resultados
        all_trades.extend(trades_log) 
        backtest_objects[symbol] = bt_obj
        
        # Recolección de estadísticas resumidas con protección contra pd.NA
        resultados_finales.append({
            "Symbol": symbol,
            "Sharpe Ratio": round(float(stats_dict.get("Sharpe Ratio") if pd.notna(stats_dict.get("Sharpe Ratio")) else 0.0), 2),
            "Max. Drawdown [%]": round(float(stats_dict.get("Max. Drawdown [%]") if pd.notna(stats_dict.get("Max. Drawdown [%]")) else 0.0), 2),
            "Profit Factor": round(float(stats_dict.get("Profit Factor") if pd.notna(stats_dict.get("Profit Factor")) else 0.0), 2),
            "Return [%]": round(float(stats_dict.get("Return [%]") if pd.notna(stats_dict.get("Return [%]")) else 0.0), 2),
            "Total Trades": int(stats_dict.get("# Trades", 0)),
            "Win Rate [%]": round(float(stats_dict.get("Win Rate [%]") if pd.notna(stats_dict.get("Win Rate [%]")) else 0.0), 2),
        })
            
    resultados_df = pd.DataFrame(resultados_finales)
    trades_df = pd.DataFrame(all_trades)
    
    # 🔧 ORDENAR TRADES POR FECHA (Fix para problema multi-símbolo temporal)
    if not trades_df.empty and 'Fecha' in trades_df.columns:
        trades_df = trades_df.sort_values('Fecha').reset_index(drop=True)
    elif not trades_df.empty and 'Entry Time' in trades_df.columns:
        trades_df = trades_df.sort_values('Entry Time').reset_index(drop=True)
    
    return resultados_df, trades_df, backtest_objects