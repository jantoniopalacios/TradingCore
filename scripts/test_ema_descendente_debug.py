#!/usr/bin/env python3
"""
TEST DE DEBUG: Monitorea qué ocurre con ema_slow_descendente_STATE durante la ejecución.
Añade logging a la función check_ema_sell_signal() para diagnosticar por qué no se cierran posiciones.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def test_ema_descendente_debug():
    """Ejecuta backtest con logging de estado EMA."""
    
    print("\n" + "="*80)
    print("TEST: EMA Descendente STATE Debug")
    print("="*80)
    
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
            'stoploss_percentage_below_close': 5.0,  # 5% SL
            
            # ===== EMA: ONLY DESCENDENTE ENABLED =====
            'ema_cruce_signal': False,
            'ema_slow_ascendente': False,      # DISABLED - NO buys
            'ema_slow_minimo': False,
            'ema_slow_maximo': False,
            'ema_slow_descendente': True,      # ACTIVE - sells only
            
            # RSI OFF
            'rsi': False,
            
            # Otros OFF
            'macd': False,
            'stoch_fast': False,
            'stoch_mid': False,
            'stoch_slow': False,
            'bb_active': False,
            
            'activo': 'NKE',
        }
        
        try:
            print("\nEjecutando backtest con SOLO Descendente para venta...")
            resultados = ejecutar_backtest(config)
            
            if resultados is not None and len(resultados) > 0:
                import pandas as pd
                resultados_df = resultados[0]
                trades_df = resultados[1] if len(resultados) > 1 else pd.DataFrame()
                
                if resultados_df is None or resultados_df.empty:
                    print("❌ Backtest failed or returned no data")
                    return
                    
                stats = trades_df  # Usar trades_df como variable para compatibilidad
            
            print(f"\n✓ Backtest completado")
            print(f"  Total de trades: {len(trades)}")
            
            # Contar por tipo y descripción
            compras = [t for t in trades if t.get('Tipo') == 'COMPRA']
            ventas = [t for t in trades if t.get('Tipo') == 'VENTA']
            
            print(f"  Compras: {len(compras)}")
            print(f"  Ventas: {len(ventas)}")
            
            if len(ventas) == 0:
                print("\n⚠️  CRÍTICO: 0 cierres = no se abrieron posiciones (sin compras esperadas)")
            
            # Contar cierres por razón
            closes_by_reason = {}
            for t in ventas:
                desc = t.get('Descripcion', 'DESCONOCIDO')
                closes_by_reason[desc] = closes_by_reason.get(desc, 0) + 1
            
            print(f"\n📊 ANÁLISIS DE CIERRES (por descripción):")
            total_closes = len(ventas)
            for reason, count in sorted(closes_by_reason.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total_closes * 100) if total_closes > 0 else 0
                print(f"  {reason}: {count} ({pct:.1f}%)")
            
            # Diagnóstico
            print("\n" + "="*80)
            print("DIAGNÓSTICO")
            print("="*80)
            
            if len(compras) == 0:
                print("\n✓ ESPERADO: Sin compras (ema_slow_ascendente=False)")
            
            if "EMA Lenta Descendente" not in closes_by_reason:
                print("\n❌ PROBLEMA: No hay cierres con 'EMA Lenta Descendente'")
                print("   - ema_slow_descendente_STATE probablemente no es True")
                print("   - O check_ema_sell_signal() no se llama")
                print("   - O las posiciones se cierran por StopLoss antes")
            else:
                print(f"\n✓ 'EMA Lenta Descendente' generó {closes_by_reason['EMA Lenta Descendente']} cierres")
            
            print("\n" + "="*80)
            
        except Exception as e:
            print(f"\n❌ Error durante backtest: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_ema_descendente_debug()

