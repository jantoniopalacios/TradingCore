"""
Módulo: DBStore.py
Responsabilidad: Persistencia robusta de resultados de backtesting.
Diseño: Capa de abstracción que limpia y valida datos antes de la inserción en SQL.
"""

import json
import logging
import numpy as np
import pandas as pd
from .database import db, ResultadoBacktest, Trade

logger = logging.getLogger(__name__)

def _clean_value(val, default=0.0, dtype=float):
    """
    Limpia valores conflictivos (N/A, NaN, Inf) generados por motores de cálculo.
    Evita que el hilo de ejecución se rompa por errores de conversión.
    """
    if val is None or (isinstance(val, str) and val.strip().upper() in ['N/A', 'NAN', 'NONE', '']):
        return dtype(default)
    try:
        # Manejo de infinitos para datos financieros
        if dtype == float:
            v = float(val)
            return v if np.isfinite(v) else default
        return dtype(val)
    except (ValueError, TypeError):
        return dtype(default)

def save_backtest_run(user_id, stats, config_dict, trades_df, grafico_html=None):
    """
    Gestiona la persistencia de un backtest completo en PostgreSQL.
    Normaliza los datos de entrada para asegurar compatibilidad con el esquema.
    """
    try:
        # 1. Mapeo de Parámetros Técnicos a JSON seguro
        # Solo guardamos tipos primitivos para evitar errores de serialización
        serializable_config = {
            str(k): v for k, v in config_dict.items() 
            if isinstance(v, (int, float, str, bool))
        }

        # 2. Creación del registro maestro (Resultado)
        # Usamos nombres de columnas estándar de backtesting.py con limpieza integrada
        nuevo_resultado = ResultadoBacktest(
            usuario_id=user_id,
            id_estrategia=_clean_value(config_dict.get('tanda_id'), 1, int),
            symbol=str(stats.get('Symbol', config_dict.get('SYMBOL', 'N/A'))),
            
            # Métricas de Performance
            return_pct=_clean_value(stats.get('Return [%]')),
            max_drawdown=_clean_value(stats.get('Max. Drawdown [%]')),
            sharpe_ratio=_clean_value(stats.get('Sharpe Ratio')),
            profit_factor=_clean_value(stats.get('Profit Factor')),
            total_trades=_clean_value(stats.get('# Trades', stats.get('Total Trades')), 0, int),
            win_rate=_clean_value(stats.get('Win Rate [%]')),
            
            # Configuración de la ejecución
            fecha_inicio_datos=str(config_dict.get('START_DATE', config_dict.get('start_date'))),
            fecha_fin_datos=str(config_dict.get('END_DATE', config_dict.get('end_date'))),
            intervalo=str(config_dict.get('INTERVAL', '1d')),
            cash_inicial=_clean_value(config_dict.get('CASH', 10000)),
            comision=_clean_value(config_dict.get('COMMISSION', 0.0)),
            
            params_tecnicos=json.dumps(serializable_config),
            grafico_html=grafico_html
        )

        db.session.add(nuevo_resultado)
        db.session.flush()  # Genera el ID sin cerrar la transacción para vincular los trades

        # 3. Guardado detallado de Trades
        if trades_df is not None and not trades_df.empty:
            for _, row in trades_df.iterrows():
                # Normalizamos nombres de columnas (backtesting.py usa CamelCase o espacios)
                size = _clean_value(row.get('Size', 0))
                
                t = Trade(
                    backtest_id=nuevo_resultado.id,
                    tipo="BUY" if size > 0 else "SELL",
                    fecha=str(row.name), 
                    precio_entrada=_clean_value(row.get('EntryPrice', row.get('Precio_Entrada'))),
                    precio_salida=_clean_value(row.get('ExitPrice', row.get('Precio_Salida'))),
                    pnl_absoluto=_clean_value(row.get('PnL', row.get('PnL_Absoluto'))),
                    retorno_pct=_clean_value(row.get('ReturnPct', row.get('Retorno_Pct'))) * 100
                )
                db.session.add(t)

        db.session.commit()
        logger.info(f"💾 [DBStore] Éxito: {nuevo_resultado.symbol} guardado (ID: {nuevo_resultado.id}).")
        return nuevo_resultado.id

    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ [DBStore] Fallo crítico: {e}")
        raise e