#!/usr/bin/env python3
"""
TEST 1b SIMPLE: Validar EMA Fix

Objetivo: Confirmar que cuando ema_slow_ascendente=False, 
          no hay trades con EMA en la descripcion
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def test_ema_fix():
    """TEST 1b: EMA Fix Validation - EMA should NOT appear in trades"""
    
    print("="*70)
    print("TEST 1b: EMA FIX VALIDATION")
    print("="*70)
    
    from scenarios.BacktestWeb.app import create_app
    from scenarios.BacktestWeb.Backtest import ejecutar_backtest
    from scenarios.BacktestWeb.configuracion import cargar_y_asignar_configuracion
    
    app = create_app(user_mode='admin')
    
    with app.app_context():
        cargar_y_asignar_configuracion('admin')
        
        # Configurar parámetros para TEST 1b
        config = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'intervalo': '1d',
            'cash': 10000,
            'commission': 0.0,
            'stoploss_percentage_below_close': 0.0,
            
            # EMA DESACTIVADO
            'ema_cruce_signal': False,
            'ema_slow_minimo': False,
            'ema_slow_ascendente': False,  # KEY FIX
            'ema_slow_maximo': False,
            'ema_slow_descendente': False,
            
            # RSI ACTIVADO
            'rsi': True,
            'rsi_period': 14,
            'rsi_low_level': 30,
            'rsi_high_level': 70,
            'rsi_minimo': False,
            'rsi_ascendente': True,
            'rsi_maximo': False,
            'rsi_descendente': False,
            
            # Otros
            'macd': False,
            'bb_active': False,
            'filtro_fundamental': False,
            'enviar_mail': False,
            'margen_seguridad_active': False,
            'volume_active': False,
            'stoch_fast': False,
            'stoch_mid': False,
            'stoch_slow': False,
            
            'user_id': 1,
            'user_mode': 'admin',
        }
        
        print("\nConfiguration:")
        print(f"  RSI: On (period=14, ascendente=True)")
        print(f"  EMA Ascendente: False [TESTING THIS]")
        print(f"  EMA Minimo: False")
        print("\nExecuting backtest...")
        
        try:
            resultados = ejecutar_backtest(config)
            
            if resultados is not None and len(resultados) > 0:
                import pandas as pd
                resultados_df = resultados[0]
                trades_df = resultados[1] if len(resultados) > 1 else pd.DataFrame()
                
                if resultados_df is not None and not resultados_df.empty:
                    print("[SUCCESS] Backtest completed")
                    
                    if not trades_df.empty:
                        # Check for EMA and RSI trades
                        ema_trades = trades_df[
                            trades_df['Descripcion'].str.contains('EMA', case=False, na=False)
                        ]
                        rsi_trades = trades_df[
                            trades_df['Descripcion'].str.contains('RSI', case=False, na=False)
                        ]
                        
                        total = len(trades_df)
                        ema_count = len(ema_trades)
                        rsi_count = len(rsi_trades)
                        
                        print(f"\nResults:")
                        print(f"  Total trades: {total}")
                        print(f"  Trades with EMA: {ema_count} ({ema_count/total*100:.1f}%)")
                        print(f"  Trades with RSI: {rsi_count} ({rsi_count/total*100:.1f}%)")
                        
                        if ema_count == 0:
                            print("\n[PASS] EMA trades = 0 (fix is working!)")
                            print(f"       RSI generating {rsi_count} trades correctly")
                            return True
                        else:
                            print(f"\n[FAIL] EMA trades still present: {ema_count}")
                            print("       Sample descriptions:")
                            for desc in ema_trades['Descripcion'].unique()[:3]:
                                count = len(ema_trades[ema_trades['Descripcion'] == desc])
                                print(f"         - {desc}: {count}")
                            return False
                    else:
                        print("\n[INFO] No trades generated")
                        return True
                else:
                    print("\n[FAIL] No results returned")
                    return False
            else:
                print("\n[FAIL] Backtest execution failed")
                return False
                
        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    try:
        success = test_ema_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
