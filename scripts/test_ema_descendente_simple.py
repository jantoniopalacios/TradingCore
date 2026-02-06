#!/usr/bin/env python3
"""
TEST SIMPLE: Compara resultadosc on descendente ONLY vs ascendente ONLY vs ambos.
Este test verifica si la lógica de descendente está funcionando correctamente.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def run_comparison_test():
    """Ejecuta 3 backtests para comparar comportamientos."""
    
    from scenarios.BacktestWeb.app import create_app
    from scenarios.BacktestWeb.Backtest import ejecutar_backtest
    from scenarios.BacktestWeb.configuracion import cargar_y_asignar_configuracion
    
    app = create_app(user_mode='admin')
    
    with app.app_context():
        cargar_y_asignar_configuracion('admin')
        
        # Configuración base (igual para todos)
        base_config = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'intervalo': '1d',
            'cash': 10000,
            'commission': 0.0,
            'stoploss_percentage_below_close': 5.0,
            'macd': False,
            'stoch_fast': False,
            'stoch_mid': False,
            'stoch_slow': False,
            'bb_active': False,
            'rsi': False,
            'ema_cruce_signal': False,
            'ema_slow_minimo': False,
            'ema_slow_maximo': False,
            'activo': 'NKE',
        }
        
        tests = [
            ('ASCENDENTE ONLY', {'ema_slow_ascendente': True, 'ema_slow_descendente': False}),
            ('DESCENDENTE ONLY', {'ema_slow_ascendente': False, 'ema_slow_descendente': True}),
            ('BOTH', {'ema_slow_ascendente': True, 'ema_slow_descendente': True}),
        ]
        
        print("\n" + "="*80)
        print("TEST: Comparing EMA Ascendente vs Descendente Triggers")
        print("="*80)
        
        for test_name, ema_flags in tests:
            config = {**base_config, **ema_flags}
            
            print(f"\n{'-'*80}")
            print(f"TEST: {test_name}")
            print(f"  ema_slow_ascendente: {config['ema_slow_ascendente']}")
            print(f"  ema_slow_descendente: {config['ema_slow_descendente']}")
            print(f"-{'-'*79}")
            
            try:
                resultados = ejecutar_backtest(config)
                
                if resultados is None or len(resultados) == 0:
                    print("  ❌ No results")
                    continue
                
                trades_df = resultados[1] if len(resultados) > 1 else None
                
                if trades_df is None or trades_df.empty:
                    print("  ⚠️ No trades")
                    continue
                
                # Análisis básico
                total = len(trades_df)
                compras = len(trades_df[trades_df['Tipo'] == 'COMPRA'])
                ventas = len(trades_df[trades_df['Tipo'] == 'VENTA'])
                
                print(f"  Total Trades: {total} (Compras: {compras}, Ventas: {ventas})")
                
                # Análisis de triggers
                ema_asc = len(trades_df[trades_df['Descripcion'].str.contains('Ascendente', case=False, na=False)])
                ema_desc = len(trades_df[trades_df['Descripcion'].str.contains('Descendente', case=False, na=False)])
                sl = len(trades_df[trades_df['Descripcion'] == 'StopLoss'])
                
                if total > 0:
                    print(f"\n  Trigger Breakdown:")
                    print(f"    Ascendente: {ema_asc} ({ema_asc/total*100:.1f}%)")
                    print(f"    Descendente: {ema_desc} ({ema_desc/total*100:.1f}%)")
                    print(f"    StopLoss: {sl} ({sl/total*100:.1f}%)")
                    print(f"    Other: {total - ema_asc - ema_desc - sl}")
                
                # Verificación
                if test_name == 'ASCENDENTE ONLY' and ema_asc > 0:
                    print(f"  ✓ Ascendente trigger working")
                elif test_name == 'DESCENDENTE ONLY' and ema_desc > 0:
                    print(f"  ✓ Descendente trigger working")
                elif test_name == 'BOTH' and ema_asc > 0 and ema_desc > 0:
                    print(f"  ✓ Both triggers working")
                else:
                    print(f"  ❌ Expected trigger NOT found")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    run_comparison_test()
