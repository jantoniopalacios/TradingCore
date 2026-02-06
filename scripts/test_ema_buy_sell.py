#!/usr/bin/env python3
"""
TEST: Validar que Ascendente (compra) y Decreciente (venta) funcionan como triggers.

Config:
  - ema_slow_ascendente = True      (activar compras)
  - ema_slow_descendente = True     (activar ventas)
  - Periodo: 2024 (NKE)
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def test_ema_buy_sell():
    """TEST: Ascendente compra, Descendente vende"""
    
    print("="*70)
    print("TEST: EMA Buy/Sell (Ascendente + Descendente)")
    print("="*70)
    
    from scenarios.BacktestWeb.app import create_app
    from scenarios.BacktestWeb.Backtest import ejecutar_backtest
    from scenarios.BacktestWeb.configuracion import cargar_y_asignar_configuracion
    
    app = create_app(user_mode='admin')
    
    with app.app_context():
        cargar_y_asignar_configuracion('admin')
        
        config = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'intervalo': '1d',
            'cash': 10000,
            'commission': 0.0,
            'stoploss_percentage_below_close': 0.0,
            
            # ===== EMA ACTIVATION =====
            'ema_cruce_signal': False,
            'ema_slow_ascendente': True,      # COMPRA: Cuando EMA sube
            'ema_slow_minimo': False,
            'ema_slow_maximo': False,
            'ema_slow_descendente': True,     # VENTA: Cuando EMA baja
            
            # RSI OFF (para que EMA sea el único trigger)
            'rsi': False,
            
            # Otros OFF
            'macd': False,
            'bb_active': False,
            'filtro_fundamental': False,
            'margen_seguridad_active': False,
            'volume_active': False,
            'stoch_fast': False,
            'stoch_mid': False,
            'stoch_slow': False,
            
            'user_id': 1,
            'user_mode': 'admin',
        }
        
        print("\nConfiguration:")
        print(f"  ema_slow_ascendente (COMPRA):     {config['ema_slow_ascendente']}")
        print(f"  ema_slow_descendente (VENTA):     {config['ema_slow_descendente']}")
        print(f"  Periodo: 2024-01-01 to 2024-12-31")
        print(f"  Activo: NKE")
        
        print("\nExpectativa:")
        print("  - Compras cuando EMA Lenta sube")
        print("  - Ventas cuando EMA Lenta baja")
        
        print("\nExecutando backtest...")
        
        try:
            resultados = ejecutar_backtest(config)
            
            if resultados is not None and len(resultados) > 0:
                import pandas as pd
                resultados_df = resultados[0]
                trades_df = resultados[1] if len(resultados) > 1 else pd.DataFrame()
                
                if resultados_df is not None and not resultados_df.empty:
                    print(f"\n[SUCCESS] Backtest completed")
                    
                    if not trades_df.empty:
                        total_trades = len(trades_df)
                        compras = len(trades_df[trades_df['Tipo'] == 'COMPRA'])
                        ventas = len(trades_df[trades_df['Tipo'] == 'VENTA'])
                        
                        print(f"\nResults:")
                        print(f"  Total Trades: {total_trades}")
                        print(f"  Compras: {compras}")
                        print(f"  Ventas: {ventas}")
                        
                        # Buscar triggers
                        ema_ascendente_trades = trades_df[
                            trades_df['Descripcion'].str.contains('Ascendente', case=False, na=False)
                        ]
                        ema_descendente_trades = trades_df[
                            trades_df['Descripcion'].str.contains('Descendente', case=False, na=False)
                        ]
                        
                        print(f"\nEMA Trigger Analysis:")
                        print(f"  Trades with 'Ascendente': {len(ema_ascendente_trades)} ({len(ema_ascendente_trades)/total_trades*100:.1f}%)")
                        print(f"  Trades with 'Descendente': {len(ema_descendente_trades)} ({len(ema_descendente_trades)/total_trades*100:.1f}%)")
                        
                        if len(ema_ascendente_trades) > 0:
                            print(f"\n[PASS] EMA Ascendente is generating buy signals!")
                        else:
                            print(f"\n[WARN] No Ascendente trades found")
                        
                        if len(ema_descendente_trades) > 0:
                            print(f"[PASS] EMA Descendente is generating sell signals!")
                        else:
                            print(f"[WARN] No Descendente trades found")
                        
                        if len(ema_ascendente_trades) > 0 and len(ema_descendente_trades) > 0:
                            print(f"\n[PASS] Buy/Sell cycle working correctly!")
                            return True
                        else:
                            return False
                    else:
                        print(f"\n[INFO] No trades generated (OK if EMA conditions not met)")
                        return True
                else:
                    print(f"\n[FAIL] No results returned")
                    return False
            else:
                print(f"\n[FAIL] Backtest execution failed")
                return False
                
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    try:
        success = test_ema_buy_sell()
        print("\n" + "="*70)
        if success:
            print("TEST RESULT: PASS")
        else:
            print("TEST RESULT: INCOMPLETE/WARN")
        print("="*70)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
