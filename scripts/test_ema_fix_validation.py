#!/usr/bin/env python3
"""
TEST 1b: Validar EMA Fix - Que EMA NO salga en trades cuando está desactivado

Objetivo: Confirmar que después del fix en check_ema_buy_signal(), 
          los trades con EMA = 0 cuando ema_slow_ascendente=False

Parámetros:  rsi=True, rsi_ascendente=True, ema_slow_ascendente=False
Activos:     NKE únicamente
Período:     2024-01-01 to 2024-12-31
Expectativa: ZERO trades con EMA (antes had 26%)
"""
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.Backtest import ejecutar_backtest
from scenarios.BacktestWeb.configuracion import cargar_y_asignar_configuracion, System
from trading_engine.core.database_pg import db
from scenarios.BacktestWeb.database import ResultadoBacktest, Trade, Usuario, Simbolo
import pandas as pd

def test_ema_fix():
    """TEST 1b: EMA Fix Validation - EMA should NOT appear in trades"""
    
    print("="*70)
    print("TEST 1b: EMA FIX VALIDATION")
    print("="*70)
    
    app = create_app(user_mode='admin')
    
    with app.app_context():
        # 1. Cargar config base
        cargar_y_asignar_configuracion('admin')
        
        # 2. Configurar parámetros para TEST 1b
        config = {
            # Datos
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'intervalo': '1d',
            'cash': 10000,
            'commission': 0.0,
            'stoploss_percentage_below_close': 0.0,
            
            # INDICADORES
            # ❌ EMA COMPLETAMENTE DESACTIVADO (ESTO ES LO QUE ESTAMOS VALIDANDO)
            'ema_cruce_signal': False,
            'ema_slow_minimo': False,
            'ema_slow_ascendente': False,    # <-- KEY: Must be False
            'ema_slow_maximo': False,
            'ema_slow_descendente': False,   # <-- Veto on, but disabled signals
            
            # ✅ RSI ACTIVADO (PARA GENERAR TRADES)
            'rsi': True,
            'rsi_period': 14,
            'rsi_low_level': 30,
            'rsi_high_level': 70,
            'rsi_minimo': False,
            'rsi_ascendente': True,   # <-- ACTIVE
            'rsi_maximo': False,
            'rsi_descendente': False,
            
            # Otros indicadores desactivados
            'macd': False,
            'bb_active': False,
            'filtro_fundamental': False,
            'enviar_mail': False,
            'margen_seguridad_active': False,
            'volume_active': False,
            'stoch_fast': False,
            'stoch_mid': False,
            'stoch_slow': False,
            
            # Metadata
            'user_id': 1,
            'user_mode': 'admin',
            'tanda_id': 102,  # ID único para este test
        }
        
        # 🔴 ACTIVOS A PROBAR
        simbolos_test = ['NKE']
        
        for simbolo in simbolos_test:
            print(f"\n{'='*70}")
            print(f"Probando: {simbolo}")
            print(f"{'='*70}")
            
            # Actualizar configuración con el símbolo actual
            config['simbolo'] = simbolo
            config['user_id'] = config.get('user_id', 1)
            
            # Registrar símbolo en BD si no existe
            try:
                # Buscar por symbol (no nombre)
                sim_obj = db.session.query(Simbolo).filter_by(symbol=simbolo).filter_by(usuario_id=1).first()
                if not sim_obj:
                    sim_obj = Simbolo(symbol=simbolo, name=simbolo, usuario_id=1)
                    db.session.add(sim_obj)
                    db.session.commit()
            except Exception as e:
                print(f"⚠️  No DB symbol registration: {e}")
            
            # Ejecutar backtest
            resultados = ejecutar_backtest(config)
            
            # Analizar resultado
            if resultados is not None and len(resultados) > 0:
                resultados_df = resultados[0]
                trades_df_result = resultados[1] if len(resultados) > 1 else pd.DataFrame()
                
                if resultados_df is not None and not resultados_df.empty:
                    print(f"\n✅ Backtest completado para {simbolo}")
                    
                    # Estadísticas principales
                    print(f"  Return: {resultados_df[resultados_df['Symbol'] == simbolo].get('Return [%]', ['N/A']).iloc[0]}%")
                    
                    # Verificar si hay trades con EMA (basándonos en descripción de trades)
                    try:
                        if not trades_df_result.empty:
                            trades_symbol = trades_df_result[trades_df_result['Symbol'] == simbolo]
                            print(f"\n  Analyzing {len(trades_symbol)} trades...")
                            
                            ema_trades = trades_symbol[
                                trades_symbol['Descripcion'].str.contains('EMA', case=False, na=False)
                            ]
                            rsi_trades = trades_symbol[
                                trades_symbol['Descripcion'].str.contains('RSI', case=False, na=False)
                            ]
                            
                            total_trades = len(trades_symbol)
                            print(f"\n  📊 Trade Distribution:")
                            print(f"     - Total trades: {total_trades}")
                            print(f"     - Trades with EMA: {len(ema_trades)} ({len(ema_trades)/total_trades*100:.1f}%)")
                            print(f"     - Trades with RSI: {len(rsi_trades)} ({len(rsi_trades)/total_trades*100:.1f}%)")
                            
                            if len(ema_trades) > 0:
                                print(f"\n  ⚠️  PROBLEMA ENCONTRADO: EMA trades aún presentes")
                                print(f"     Sample descriptions:")
                                for desc in ema_trades['Descripcion'].unique()[:3]:
                                    count = len(ema_trades[ema_trades['Descripcion'] == desc])
                                    print(f"       - {desc}: {count} trades")
                                return False
                            else:
                                print(f"\n  ✅ ÉXITO: NO hay trades con EMA!")
                                print(f"     RSI está correctamente generando {len(rsi_trades)} trades ({len(rsi_trades)/total_trades*100:.1f}%)")
                                return True
                        else:
                            print(f"\n  ℹ️  No trades found (could be filtered by other conditions)")
                            return True
                            
                    except Exception as e:
                        print(f"⚠️  Could not analyze trades: {e}")
                        return False
                    
                else:
                    print(f"\n❌ Backtest failed for {simbolo} - no results")
                    return False
            else:
                print(f"\n❌ Backtest failed for {simbolo}")
                return False
        
        print(f"\n✅ TEST 1b COMPLETED SUCCESSFULLY")
        return True

if __name__ == '__main__':
    try:
        success = test_ema_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

